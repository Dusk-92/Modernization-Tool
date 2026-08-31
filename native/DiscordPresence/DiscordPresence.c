/*
 * DiscordPresence.dll
 * Read-only WoW 1.12.1 (build 5875) character snapshot helper.
 *
 * It is loaded by VanillaFixes through dlls.txt and writes:
 *   <game>\.modernization_tool\DiscordPresence\discord_wow_status.json
 *   <game>\.modernization_tool\DiscordPresence\discord_broadcast_flags
 *
 * No Discord IPC is performed in-process. DiscordPresence.exe owns Discord IPC.
 * The companion is started from the DLL worker thread after WoW startup; it is
 * never launched from DllMain.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define IMAGE_BASE 0x00400000u
#define POLL_MS 2000u
#define STARTUP_DELAY_MS 6000u
#define WORLD_STABLE_MS 3000u
#define MAX_NAME 24
#define MAX_ZONE 64
#define MAX_GUILD 48
#define MAX_JSON 768
#define USER_MIN 0x00010000u
#define USER_MAX 0x7FFEFFFFu
#define MAX_OBJECT_HOPS 256
#define MAX_GUILD_HOPS 32

#define FLAG_NAME    1u
#define FLAG_GUILD   2u
#define FLAG_FACTION 4u
#define FLAG_CLASS   8u
#define FLAG_LEVEL   16u
#define FLAG_ZONE    32u
#define FLAG_ALL     63u

#define DBCACHE_BASE_VA 0x00C0E0C0u
#define DBCACHE_STRIDE  0x3Cu
#define DBCACHE_COUNT   12
#define FOURCC_WGLD     0x444C4757u
#define FOURCC_DLGW     0x57474C44u

typedef struct {
    uintptr_t name_va[4];
    uintptr_t zone_va[6];
    uintptr_t object_manager_va;
    uint32_t first_object;
    uint32_t local_guid;
    uint32_t next_object;
    uint32_t object_type;
    uint32_t object_guid;
    uint32_t descriptors;
    uint32_t unit_level;
    uint32_t unit_bytes0;
    uint32_t player_guildid;
    uint32_t player_info;
    uint32_t guild_key;
} Layout;

static const Layout kLayout = {
    {0x00C27FC8u, 0x00C27D88u, 0x00C27FD8u, 0},
    {0x00B4B404u, 0x00B4B424u, 0x00CE06D0u, 0x00CE06F8u, 0x00B4B3C8u, 0},
    0x00B41414u,
    0xACu, 0xC0u, 0x3Cu, 0x14u, 0x30u, 0x08u,
    0x88u, 0x90u, 0x2FCu, 0xE68u, 0x0Cu
};

static HANDLE g_stop = NULL;
static HANDLE g_thread = NULL;
static DWORD g_stable_tick = 0;

static int is_user_ptr(uintptr_t p) {
    return p >= USER_MIN && p <= USER_MAX;
}

static uintptr_t runtime_va(uintptr_t original_va) {
    uintptr_t base = (uintptr_t)GetModuleHandleA(NULL);
    if (!base || original_va < IMAGE_BASE) return 0;
    return base + (original_va - IMAGE_BASE);
}

static int readable(uintptr_t address, size_t bytes) {
    MEMORY_BASIC_INFORMATION mbi;
    uintptr_t last;
    if (!address || !bytes || bytes > 4096) return 0;
    last = address + bytes - 1;
    if (last < address || !is_user_ptr(address) || !is_user_ptr(last)) return 0;
    if (!VirtualQuery((LPCVOID)address, &mbi, sizeof(mbi))) return 0;
    if (mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return 0;
    switch (mbi.Protect & 0xFFu) {
    case PAGE_READONLY:
    case PAGE_READWRITE:
    case PAGE_WRITECOPY:
    case PAGE_EXECUTE_READ:
    case PAGE_EXECUTE_READWRITE:
    case PAGE_EXECUTE_WRITECOPY:
        return 1;
    default:
        return 0;
    }
}

static int safe_read(uintptr_t address, void *out, size_t bytes) {
    SIZE_T got = 0;
    if (!out || !readable(address, bytes)) return 0;
    return ReadProcessMemory(GetCurrentProcess(), (LPCVOID)address, out, bytes, &got)
        && got == bytes;
}

static int read_u32(uintptr_t address, uint32_t *out) {
    uint32_t value = 0;
    if (!out || !safe_read(address, &value, sizeof(value))) return 0;
    *out = value;
    return 1;
}

static int read_u64(uintptr_t address, uint64_t *out) {
    uint64_t value = 0;
    if (!out || !safe_read(address, &value, sizeof(value))) return 0;
    *out = value;
    return 1;
}

static int copy_ascii_string(uintptr_t address, char *out, size_t out_size, size_t max_len) {
    char temp[128];
    SIZE_T got = 0;
    size_t want, i;
    if (!out || out_size < 2 || !is_user_ptr(address)) return 0;
    out[0] = 0;
    want = max_len + 1;
    if (want > sizeof(temp)) want = sizeof(temp);
    if (want > out_size) want = out_size;
    if (!readable(address, 1)) return 0;
    memset(temp, 0, sizeof(temp));
    if (!ReadProcessMemory(GetCurrentProcess(), (LPCVOID)address, temp, want, &got) || got == 0)
        return 0;
    if (got >= sizeof(temp)) got = sizeof(temp) - 1;
    temp[got] = 0;
    for (i = 0; i < got && i + 1 < out_size && i < max_len; ++i) {
        unsigned char c = (unsigned char)temp[i];
        if (c == 0) {
            out[i] = 0;
            return i > 0;
        }
        if (c < 32 || c >= 127) return 0;
        out[i] = (char)c;
    }
    out[0] = 0;
    return 0;
}

static int valid_name(const char *s) {
    size_t i, n;
    if (!s) return 0;
    n = strlen(s);
    if (n < 2 || n > 16) return 0;
    for (i = 0; i < n; ++i) {
        char c = s[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (i > 0 && c == '\'')))
            return 0;
    }
    return 1;
}

static int valid_text(const char *s, size_t max_len) {
    size_t i, n;
    if (!s) return 0;
    n = strlen(s);
    if (n < 2 || n > max_len) return 0;
    for (i = 0; i < n; ++i) {
        char c = s[i];
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
            (c >= '0' && c <= '9') || c == ' ' || c == '\'' || c == '-' || c == ':')
            continue;
        return 0;
    }
    return 1;
}

static int try_direct_or_pointer(uintptr_t va, char *out, size_t out_size, size_t max_len,
                                 int (*validator)(const char *)) {
    uintptr_t slot = runtime_va(va);
    uint32_t ptr = 0;
    if (!slot) return 0;
    if (copy_ascii_string(slot, out, out_size, max_len) && validator(out)) return 1;
    out[0] = 0;
    if (read_u32(slot, &ptr) && is_user_ptr((uintptr_t)ptr) &&
        copy_ascii_string((uintptr_t)ptr, out, out_size, max_len) && validator(out))
        return 1;
    out[0] = 0;
    return 0;
}

static int valid_zone_adapter(const char *s) { return valid_text(s, MAX_ZONE); }
static int valid_guild_adapter(const char *s) {
    if (!valid_text(s, MAX_GUILD)) return 0;
    return _stricmp(s, "none") != 0;
}

static const char *class_name(uint32_t id) {
    switch (id) {
    case 1: return "Warrior"; case 2: return "Paladin"; case 3: return "Hunter";
    case 4: return "Rogue"; case 5: return "Priest"; case 7: return "Shaman";
    case 8: return "Mage"; case 9: return "Warlock"; case 11: return "Druid";
    default: return "";
    }
}

static const char *race_name(uint32_t id) {
    switch (id) {
    case 1: return "Human"; case 2: return "Orc"; case 3: return "Dwarf";
    case 4: return "Night Elf"; case 5: return "Undead"; case 6: return "Tauren";
    case 7: return "Gnome"; case 8: return "Troll"; case 9: return "Goblin";
    case 10: return "Blood Elf"; case 11: return "Draenei"; case 16: return "High Elf";
    default: return "";
    }
}

static const char *faction_name(uint32_t race) {
    switch (race) {
    case 1: case 3: case 4: case 7: case 11: case 16: return "alliance";
    case 2: case 5: case 6: case 8: case 9: case 10: return "horde";
    default: return "";
    }
}

static int get_object_manager(uint32_t *manager) {
    uintptr_t slot = runtime_va(kLayout.object_manager_va);
    return slot && read_u32(slot, manager) && is_user_ptr((uintptr_t)*manager);
}

static int get_local_guid(uint64_t *guid) {
    uint32_t manager = 0;
    uint64_t a = 0, b = 0;
    if (!guid || !get_object_manager(&manager)) return 0;
    if (!read_u64((uintptr_t)manager + kLayout.local_guid, &a) ||
        !read_u64((uintptr_t)manager + kLayout.local_guid, &b) ||
        !a || a != b)
        return 0;
    *guid = a;
    return 1;
}

static uintptr_t guild_cache_instance(void) {
    int i;
    for (i = 0; i < DBCACHE_COUNT; ++i) {
        uintptr_t inst = runtime_va(DBCACHE_BASE_VA + (uintptr_t)i * DBCACHE_STRIDE);
        uint32_t fourcc = 0, file_ptr = 0;
        char filename[32] = {0};
        if (!inst || !readable(inst, 0x30)) continue;
        if (read_u32(inst + 0x28u, &fourcc) &&
            (fourcc == FOURCC_WGLD || fourcc == FOURCC_DLGW))
            return inst;
        if (read_u32(inst + 0x2Cu, &file_ptr) && is_user_ptr(file_ptr) &&
            copy_ascii_string(file_ptr, filename, sizeof(filename), 24) &&
            (strstr(filename, "uild") || strstr(filename, "UILD") ||
             strstr(filename, "WGLD") || strstr(filename, "wgld")))
            return inst;
    }
    return 0;
}

static int walk_guild_chain(uint32_t start, uint32_t key, uint32_t next_offset,
                            char *out, size_t out_size) {
    uint32_t node = start;
    int hops = 0;
    while (is_user_ptr(node) && !(node & 1u) && hops++ < MAX_GUILD_HOPS) {
        uint32_t node_key = 0, next = 0;
        if (!read_u32(node, &node_key)) return 0;
        if (node_key == key) {
            if (copy_ascii_string((uintptr_t)node + 0x1Cu, out, out_size, MAX_GUILD) &&
                valid_guild_adapter(out)) return 1;
            if (copy_ascii_string((uintptr_t)node + 0x18u, out, out_size, MAX_GUILD) &&
                valid_guild_adapter(out)) return 1;
            out[0] = 0;
            return 0;
        }
        if (!read_u32((uintptr_t)node + next_offset, &next) || next == node) return 0;
        node = next;
    }
    return 0;
}

static int lookup_guild(uint32_t key, char *out, size_t out_size) {
    uintptr_t inst = guild_cache_instance();
    uint32_t buckets = 0, mask = 0, head = 0;
    if (!key || !inst) return 0;
    if (!read_u32(inst + 0x1Cu, &buckets) || !is_user_ptr(buckets)) return 0;
    if (!read_u32(inst + 0x24u, &mask)) return 0;
    if (!read_u32((uintptr_t)buckets + (key & mask) * 12u + 8u, &head)) return 0;
    if (walk_guild_chain(head, key, 4u, out, out_size)) return 1;
    return walk_guild_chain(head, key, 8u, out, out_size);
}

static int read_player_fields(uint64_t wanted_guid, uint32_t *level, uint32_t *race,
                              uint32_t *class_id, char *guild, size_t guild_size) {
    uint32_t manager = 0, current = 0, first = 0;
    int hops = 0;
    if (!get_object_manager(&manager)) return 0;
    if (!read_u32((uintptr_t)manager + kLayout.first_object, &current) || !is_user_ptr(current))
        return 0;
    first = current;
    while (is_user_ptr(current) && !(current & 1u) && hops++ < MAX_OBJECT_HOPS) {
        uint32_t still_first = 0, type = 0, desc = 0, next = 0;
        uint64_t guid = 0;
        if (!read_u32((uintptr_t)manager + kLayout.first_object, &still_first) || still_first != first)
            return 0;
        if (!read_u32((uintptr_t)current + kLayout.object_type, &type)) return 0;
        if (type == 4 &&
            read_u64((uintptr_t)current + kLayout.object_guid, &guid) &&
            guid == wanted_guid &&
            read_u32((uintptr_t)current + kLayout.descriptors, &desc) &&
            is_user_ptr(desc)) {
            uint32_t bytes0 = 0, lv = 0, guild_id = 0, info = 0;
            if (read_u32((uintptr_t)desc + kLayout.unit_level, &lv) && lv >= 1 && lv <= 80)
                *level = lv;
            if (read_u32((uintptr_t)desc + kLayout.unit_bytes0, &bytes0)) {
                *race = bytes0 & 0xFFu;
                *class_id = (bytes0 >> 8) & 0xFFu;
            }
            guild[0] = 0;
            if (read_u32((uintptr_t)desc + kLayout.player_guildid, &guild_id) && guild_id)
                lookup_guild(guild_id, guild, guild_size);
            if (!guild[0] &&
                read_u32((uintptr_t)current + kLayout.player_info, &info) &&
                is_user_ptr(info) &&
                read_u32((uintptr_t)info + kLayout.guild_key, &guild_id) && guild_id)
                lookup_guild(guild_id, guild, guild_size);
            return 1;
        }
        if (!read_u32((uintptr_t)current + kLayout.next_object, &next) ||
            !is_user_ptr(next) || next == current)
            return 0;
        current = next;
    }
    return 0;
}

static int game_directory(char *out, size_t out_size) {
    char exe[MAX_PATH];
    char *slash;

    if (!out || out_size < 4) return 0;
    if (!GetModuleFileNameA(NULL, exe, MAX_PATH)) return 0;
    slash = strrchr(exe, '\\');
    if (!slash) slash = strrchr(exe, '/');
    if (!slash) return 0;
    *slash = 0;
    if (strlen(exe) + 1 > out_size) return 0;
    lstrcpynA(out, exe, (int)out_size);
    return 1;
}

static int start_discord_companion(void) {
    char root[MAX_PATH];
    char exe[MAX_PATH];
    char command[MAX_PATH * 2];
    DWORD attrs;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    if (!game_directory(root, sizeof(root))) return 0;
    if (strlen(root) + strlen("\\DiscordPresence.exe") + 1 >= sizeof(exe)) return 0;

    _snprintf(exe, sizeof(exe), "%s\\DiscordPresence.exe", root);
    exe[sizeof(exe) - 1] = 0;

    attrs = GetFileAttributesA(exe);
    if (attrs == INVALID_FILE_ATTRIBUTES || (attrs & FILE_ATTRIBUTE_DIRECTORY)) return 0;

    _snprintf(
        command,
        sizeof(command),
        "\"%s\" --pid %lu",
        exe,
        (unsigned long)GetCurrentProcessId());
    command[sizeof(command) - 1] = 0;

    memset(&si, 0, sizeof(si));
    memset(&pi, 0, sizeof(pi));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    if (!CreateProcessA(
            exe,
            command,
            NULL,
            NULL,
            FALSE,
            CREATE_NO_WINDOW,
            NULL,
            root,
            &si,
            &pi)) {
        return 0;
    }

    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 1;
}

static int data_dir(char *out, size_t out_size) {
    char exe[MAX_PATH], root[MAX_PATH], support[MAX_PATH];
    char *slash;
    size_t need;
    if (!out || out_size < 64) return 0;
    if (!GetModuleFileNameA(NULL, exe, MAX_PATH)) return 0;
    slash = strrchr(exe, '\\');
    if (!slash) slash = strrchr(exe, '/');
    if (!slash) return 0;
    *slash = 0;

    need = strlen(exe) + strlen("\\.modernization_tool") + 1;
    if (need >= sizeof(support)) return 0;
    _snprintf(support, sizeof(support), "%s\\.modernization_tool", exe);
    support[sizeof(support) - 1] = 0;
    CreateDirectoryA(support, NULL);

    need = strlen(support) + strlen("\\DiscordPresence") + 1;
    if (need >= sizeof(root)) return 0;
    _snprintf(root, sizeof(root), "%s\\DiscordPresence", support);
    root[sizeof(root) - 1] = 0;
    CreateDirectoryA(root, NULL);

    if (strlen(root) + 1 > out_size) return 0;
    lstrcpynA(out, root, (int)out_size);
    return 1;
}

static int data_file(char *out, size_t out_size, const char *name) {
    char dir[MAX_PATH];
    if (!data_dir(dir, sizeof(dir))) return 0;
    if (strlen(dir) + 1 + strlen(name) + 1 > out_size) return 0;
    _snprintf(out, out_size, "%s\\%s", dir, name);
    out[out_size - 1] = 0;
    return 1;
}

static unsigned broadcast_flags(void) {
    char path[MAX_PATH], buffer[32] = {0};
    HANDLE file;
    DWORD got = 0;
    char *end = NULL;
    unsigned value;
    if (!data_file(path, sizeof(path), "discord_broadcast_flags")) return FLAG_ALL;
    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                       OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return FLAG_ALL;
    if (!ReadFile(file, buffer, sizeof(buffer) - 1, &got, NULL) || got == 0) {
        CloseHandle(file);
        return FLAG_ALL;
    }
    CloseHandle(file);
    value = (unsigned)strtoul(buffer, &end, 10);
    return end == buffer ? FLAG_ALL : (value & FLAG_ALL);
}

static void json_escape(const char *in, char *out, size_t out_size) {
    size_t r = 0, w = 0;
    if (!out || !out_size) return;
    while (in && in[r] && w + 2 < out_size) {
        unsigned char c = (unsigned char)in[r++];
        if (c == '"' || c == '\\') {
            if (w + 3 >= out_size) break;
            out[w++] = '\\';
            out[w++] = (char)c;
        } else if (c >= 32 && c < 127) {
            out[w++] = (char)c;
        }
    }
    out[w] = 0;
}

static int write_json(const char *json) {
    char target[MAX_PATH], temp[MAX_PATH];
    HANDLE file;
    DWORD wanted, written = 0;
    if (!json || !data_file(target, sizeof(target), "discord_wow_status.json")) return 0;
    if (strlen(target) + 5 >= sizeof(temp)) return 0;
    _snprintf(temp, sizeof(temp), "%s.tmp", target);
    temp[sizeof(temp) - 1] = 0;
    file = CreateFileA(temp, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    wanted = (DWORD)strlen(json);
    if (!WriteFile(file, json, wanted, &written, NULL) || written != wanted) {
        CloseHandle(file);
        DeleteFileA(temp);
        return 0;
    }
    FlushFileBuffers(file);
    CloseHandle(file);
    if (!MoveFileExA(temp, target, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        DeleteFileA(temp);
        return 0;
    }
    return 1;
}

static void publish_snapshot(void) {
    char name[MAX_NAME + 1] = {0};
    char zone[MAX_ZONE + 1] = {0};
    char guild[MAX_GUILD + 1] = {0};
    char ename[MAX_NAME * 2 + 8], ezone[MAX_ZONE * 2 + 8], eguild[MAX_GUILD * 2 + 8];
    char json[MAX_JSON];
    uint32_t level = 0, race = 0, class_id = 0;
    uint64_t guid = 0;
    unsigned flags;
    int have_name = 0, have_zone = 0, i;
    DWORD now = GetTickCount();

    for (i = 0; kLayout.name_va[i]; ++i) {
        if (try_direct_or_pointer(kLayout.name_va[i], name, sizeof(name), MAX_NAME, valid_name)) {
            have_name = 1;
            break;
        }
    }
    for (i = 0; kLayout.zone_va[i]; ++i) {
        if (try_direct_or_pointer(kLayout.zone_va[i], zone, sizeof(zone), MAX_ZONE, valid_zone_adapter)) {
            have_zone = 1;
            break;
        }
    }

    if (have_name && have_zone) {
        if (!g_stable_tick) g_stable_tick = now ? now : 1;
        if ((now - g_stable_tick) >= WORLD_STABLE_MS && get_local_guid(&guid))
            read_player_fields(guid, &level, &race, &class_id, guild, sizeof(guild));
    } else {
        g_stable_tick = 0;
    }

    flags = broadcast_flags();
    json_escape((flags & FLAG_NAME) ? name : "", ename, sizeof(ename));
    json_escape((flags & FLAG_ZONE) ? zone : "", ezone, sizeof(ezone));
    json_escape((flags & FLAG_GUILD) ? guild : "", eguild, sizeof(eguild));

    _snprintf(
        json, sizeof(json),
        "{\"v\":1,\"ts\":%ld,\"ok\":%s,\"in_world\":%s,"
        "\"name\":\"%s\",\"zone\":\"%s\",\"level\":%u,"
        "\"faction\":\"%s\",\"class\":\"%s\",\"guild\":\"%s\","
        "\"race\":\"%s\",\"build\":5875,\"err\":\"%s\"}",
        (long)time(NULL),
        (have_name && have_zone) ? "true" : "false",
        (have_name && have_zone) ? "true" : "false",
        ename,
        ezone,
        (have_name && have_zone && (flags & FLAG_LEVEL)) ? level : 0,
        (have_name && have_zone && (flags & FLAG_FACTION)) ? faction_name(race) : "",
        (have_name && have_zone && (flags & FLAG_CLASS)) ? class_name(class_id) : "",
        eguild,
        (have_name && have_zone) ? race_name(race) : "",
        (have_name && have_zone) ? "" : "offsets"
    );
    json[sizeof(json) - 1] = 0;
    write_json(json);
}

static DWORD WINAPI worker_thread(LPVOID unused) {
    int companion_started = 0;
    (void)unused;

    if (WaitForSingleObject(g_stop, STARTUP_DELAY_MS) != WAIT_TIMEOUT) return 0;

    do {
#ifdef _MSC_VER
        __try {
            publish_snapshot();
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            write_json("{\"v\":1,\"ts\":0,\"ok\":false,\"in_world\":false,\"name\":\"\","
                       "\"zone\":\"\",\"level\":0,\"faction\":\"\",\"class\":\"\","
                       "\"guild\":\"\",\"race\":\"\",\"build\":5875,\"err\":\"fault\"}");
        }
#else
        publish_snapshot();
#endif

        /* Start the out-of-process Discord client only after WoW has finished
         * its initial startup delay and after the first status snapshot exists.
         * A failed start is harmless and will be retried on the next poll. */
        if (!companion_started) {
            companion_started = start_discord_companion();
        }
    } while (WaitForSingleObject(g_stop, POLL_MS) == WAIT_TIMEOUT);

    return 0;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(instance);
        g_stop = CreateEventA(NULL, TRUE, FALSE, NULL);
        if (g_stop)
            g_thread = CreateThread(NULL, 0, worker_thread, NULL, 0, NULL);
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_stop) SetEvent(g_stop);
        if (g_thread) {
            WaitForSingleObject(g_thread, 1500);
            CloseHandle(g_thread);
            g_thread = NULL;
        }
        if (g_stop) {
            CloseHandle(g_stop);
            g_stop = NULL;
        }
    }
    return TRUE;
}
