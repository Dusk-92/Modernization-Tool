/*
 * DiscordPresence.dll
 * Read-only WoW 1.12.1 (build 5875) status sampler for Modernization Tool.
 *
 * Runtime contract:
 *   <game>\.modernization_tool\DiscordPresence\discord_wow_status.json
 *   <game>\.modernization_tool\DiscordPresence\discord_broadcast_flags
 *
 * Discord IPC is intentionally out of process. After the first sample, this
 * DLL starts DiscordPresence.exe from its worker thread and passes the exact
 * WoW process id. No process launch is performed from DllMain.
 *
 * This implementation is organized independently around a small memory-view
 * layer and a snapshot serializer. Client addresses are the community-known
 * WoW 1.12.1 / build 5875 values used for compatibility with the target client.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define CLIENT_IMAGE_BASE          0x00400000u
#define CLIENT_OBJECT_MANAGER_VA   0x00B41414u
#define OM_FIRST_OBJECT_OFF        0xACu
#define OM_LOCAL_GUID_OFF          0xC0u
#define OBJECT_NEXT_OFF            0x3Cu
#define OBJECT_TYPE_OFF            0x14u
#define OBJECT_GUID_OFF            0x30u
#define OBJECT_DESCRIPTORS_OFF     0x08u
#define UNIT_LEVEL_OFF             0x88u
#define UNIT_BYTES0_OFF            0x90u
#define PLAYER_GUILD_ID_OFF        0x2FCu
#define PLAYER_INFO_OFF            0xE68u
#define PLAYER_INFO_GUILD_KEY_OFF  0x0Cu

#define GUILD_CACHE_BASE_VA        0x00C0E0C0u
#define GUILD_CACHE_STRIDE         0x3Cu
#define GUILD_CACHE_COUNT          12u
#define GUILD_TAG_WGLD             0x444C4757u
#define GUILD_TAG_DLGW             0x57474C44u

#define USER_ADDRESS_MIN           0x00010000u
#define USER_ADDRESS_MAX           0x7FFEFFFFu
#define PLAYER_OBJECT_TYPE         4u
#define MAX_OBJECT_VISITS          256u
#define MAX_GUILD_VISITS           32u

#define STARTUP_WAIT_MS            6000u
#define SAMPLE_PERIOD_MS           2000u
#define WORLD_SETTLE_MS            3000u

#define NAME_LIMIT                 24u
#define ZONE_LIMIT                 64u
#define GUILD_LIMIT                48u
#define JSON_BUFFER_SIZE           768u

#define SHARE_NAME                 1u
#define SHARE_GUILD                2u
#define SHARE_FACTION              4u
#define SHARE_CLASS                8u
#define SHARE_LEVEL                16u
#define SHARE_ZONE                 32u
#define SHARE_ALL                  63u

static const uintptr_t kPlayerNameLocations[] = {
    0x00C27FC8u, 0x00C27D88u, 0x00C27FD8u, 0
};

static const uintptr_t kZoneNameLocations[] = {
    0x00B4B404u, 0x00B4B424u, 0x00CE06D0u,
    0x00CE06F8u, 0x00B4B3C8u, 0
};

typedef struct MemoryView {
    HANDLE process;
    uintptr_t module_base;
} MemoryView;

typedef struct CharacterSnapshot {
    int in_world;
    char name[NAME_LIMIT + 1];
    char zone[ZONE_LIMIT + 1];
    char guild[GUILD_LIMIT + 1];
    uint32_t level;
    uint32_t race_id;
    uint32_t class_id;
} CharacterSnapshot;

typedef struct LabelEntry {
    uint32_t id;
    const char *text;
} LabelEntry;

static const LabelEntry kClassLabels[] = {
    {1u, "Warrior"}, {2u, "Paladin"}, {3u, "Hunter"}, {4u, "Rogue"},
    {5u, "Priest"}, {7u, "Shaman"}, {8u, "Mage"}, {9u, "Warlock"},
    {11u, "Druid"}, {0u, ""}
};

static const LabelEntry kRaceLabels[] = {
    {1u, "Human"}, {2u, "Orc"}, {3u, "Dwarf"}, {4u, "Night Elf"},
    {5u, "Undead"}, {6u, "Tauren"}, {7u, "Gnome"}, {8u, "Troll"},
    {9u, "Goblin"}, {10u, "High Elf"}, {11u, "Draenei"},
    {16u, "High Elf"}, {0u, ""}
};

static HANDLE gStopEvent = NULL;
static HANDLE gWorkerThread = NULL;
static DWORD gWorldReadySince = 0;

static int user_address(uintptr_t value) {
    return value >= (uintptr_t)USER_ADDRESS_MIN && value <= (uintptr_t)USER_ADDRESS_MAX;
}

static int readable_protection(DWORD protection) {
    DWORD base = protection & 0xFFu;
    if (protection & (PAGE_GUARD | PAGE_NOACCESS)) return 0;
    return base == PAGE_READONLY || base == PAGE_READWRITE ||
           base == PAGE_WRITECOPY || base == PAGE_EXECUTE_READ ||
           base == PAGE_EXECUTE_READWRITE || base == PAGE_EXECUTE_WRITECOPY;
}

static int readable_range(uintptr_t start, size_t length) {
    uintptr_t cursor, end;
    if (!start || !length || length > 4096u) return 0;
    end = start + length - 1u;
    if (end < start || !user_address(start) || !user_address(end)) return 0;

    cursor = start;
    while (cursor <= end) {
        MEMORY_BASIC_INFORMATION info;
        uintptr_t region_end;
        if (!VirtualQuery((LPCVOID)cursor, &info, sizeof(info))) return 0;
        if (info.State != MEM_COMMIT || !readable_protection(info.Protect)) return 0;
        region_end = (uintptr_t)info.BaseAddress + info.RegionSize;
        if (region_end <= cursor) return 0;
        if (region_end > end) return 1;
        cursor = region_end;
    }
    return 1;
}

static void memory_view_init(MemoryView *view) {
    if (!view) return;
    view->process = GetCurrentProcess();
    view->module_base = (uintptr_t)GetModuleHandleA(NULL);
}

static uintptr_t client_address(const MemoryView *view, uintptr_t vanilla_va) {
    if (!view || !view->module_base || vanilla_va < CLIENT_IMAGE_BASE) return 0;
    return view->module_base + (vanilla_va - CLIENT_IMAGE_BASE);
}

static int memory_copy(const MemoryView *view, uintptr_t address, void *destination, size_t length) {
    SIZE_T copied = 0;
    if (!view || !view->process || !destination || !readable_range(address, length)) return 0;
    if (!ReadProcessMemory(view->process, (LPCVOID)address, destination, length, &copied)) return 0;
    return copied == length;
}

static int memory_u32(const MemoryView *view, uintptr_t address, uint32_t *value) {
    uint32_t temp = 0;
    if (!value || !memory_copy(view, address, &temp, sizeof(temp))) return 0;
    *value = temp;
    return 1;
}

static int memory_u64(const MemoryView *view, uintptr_t address, uint64_t *value) {
    uint64_t temp = 0;
    if (!value || !memory_copy(view, address, &temp, sizeof(temp))) return 0;
    *value = temp;
    return 1;
}

static int memory_ascii(const MemoryView *view, uintptr_t address, char *output,
                        size_t output_size, size_t max_chars) {
    size_t i;
    if (!view || !output || output_size < 2u || !max_chars || !user_address(address)) return 0;
    output[0] = 0;
    if (max_chars + 1u > output_size) max_chars = output_size - 1u;

    for (i = 0; i <= max_chars; ++i) {
        unsigned char ch = 0;
        if (!memory_copy(view, address + i, &ch, 1u)) {
            output[0] = 0;
            return 0;
        }
        if (ch == 0) {
            output[i] = 0;
            return i > 0u;
        }
        if (i == max_chars || ch < 32u || ch >= 127u) {
            output[0] = 0;
            return 0;
        }
        output[i] = (char)ch;
    }
    output[0] = 0;
    return 0;
}

static int ascii_letter(char ch) {
    return (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z');
}

static int valid_player_name(const char *text) {
    size_t i, length;
    if (!text) return 0;
    length = strlen(text);
    if (length < 2u || length > 16u || !ascii_letter(text[0])) return 0;
    for (i = 1u; i < length; ++i) {
        if (!ascii_letter(text[i]) && text[i] != '\'') return 0;
    }
    return 1;
}

static int valid_display_text(const char *text, size_t max_length) {
    size_t i, length;
    if (!text) return 0;
    length = strlen(text);
    if (length < 2u || length > max_length) return 0;
    for (i = 0u; i < length; ++i) {
        char ch = text[i];
        if (ascii_letter(ch) || (ch >= '0' && ch <= '9') || ch == ' ' ||
            ch == '\'' || ch == '-' || ch == ':') {
            continue;
        }
        return 0;
    }
    return 1;
}

static int valid_zone_name(const char *text) {
    return valid_display_text(text, ZONE_LIMIT);
}

static int valid_guild_name(const char *text) {
    if (!valid_display_text(text, GUILD_LIMIT)) return 0;
    return _stricmp(text, "none") != 0;
}

static int text_from_location(const MemoryView *view, uintptr_t vanilla_va,
                              char *output, size_t output_size, size_t max_chars,
                              int (*validator)(const char *)) {
    uintptr_t location;
    uint32_t indirect = 0;
    if (!view || !validator) return 0;
    location = client_address(view, vanilla_va);
    if (!location) return 0;

    if (memory_ascii(view, location, output, output_size, max_chars) && validator(output))
        return 1;

    output[0] = 0;
    if (!memory_u32(view, location, &indirect) || !user_address((uintptr_t)indirect)) return 0;
    if (memory_ascii(view, (uintptr_t)indirect, output, output_size, max_chars) && validator(output))
        return 1;
    output[0] = 0;
    return 0;
}

static int first_text_match(const MemoryView *view, const uintptr_t *locations,
                            char *output, size_t output_size, size_t max_chars,
                            int (*validator)(const char *)) {
    size_t i;
    if (!locations) return 0;
    for (i = 0u; locations[i] != 0u; ++i) {
        if (text_from_location(view, locations[i], output, output_size, max_chars, validator))
            return 1;
    }
    if (output && output_size) output[0] = 0;
    return 0;
}

static const char *label_for_id(const LabelEntry *table, uint32_t id) {
    size_t i;
    if (!table || !id) return "";
    for (i = 0u; table[i].id != 0u; ++i) {
        if (table[i].id == id) return table[i].text;
    }
    return "";
}

static const char *faction_for_race(uint32_t race_id) {
    switch (race_id) {
    case 1u: case 3u: case 4u: case 7u: case 10u: case 11u: case 16u:
        return "alliance";
    case 2u: case 5u: case 6u: case 8u: case 9u:
        return "horde";
    default:
        return "";
    }
}

static int object_manager_pointer(const MemoryView *view, uint32_t *manager) {
    uintptr_t slot;
    uint32_t value = 0;
    if (!view || !manager) return 0;
    slot = client_address(view, CLIENT_OBJECT_MANAGER_VA);
    if (!slot || !memory_u32(view, slot, &value) || !user_address((uintptr_t)value)) return 0;
    *manager = value;
    return 1;
}

static int stable_local_guid(const MemoryView *view, uint32_t manager, uint64_t *guid) {
    uint64_t first = 0, second = 0;
    uintptr_t address;
    if (!view || !guid || !user_address((uintptr_t)manager)) return 0;
    address = (uintptr_t)manager + OM_LOCAL_GUID_OFF;
    if (!memory_u64(view, address, &first) || !memory_u64(view, address, &second)) return 0;
    if (!first || first != second) return 0;
    *guid = first;
    return 1;
}

static int contains_guild_marker(const char *text) {
    char lowered[32];
    size_t i, length;
    if (!text) return 0;
    length = strlen(text);
    if (length >= sizeof(lowered)) length = sizeof(lowered) - 1u;
    for (i = 0u; i < length; ++i) {
        char ch = text[i];
        lowered[i] = (ch >= 'A' && ch <= 'Z') ? (char)(ch - 'A' + 'a') : ch;
    }
    lowered[length] = 0;
    return strstr(lowered, "guild") != NULL || strstr(lowered, "wgld") != NULL;
}

static uintptr_t locate_guild_cache(const MemoryView *view) {
    unsigned i;
    for (i = 0u; i < GUILD_CACHE_COUNT; ++i) {
        uintptr_t candidate = client_address(
            view, GUILD_CACHE_BASE_VA + (uintptr_t)i * GUILD_CACHE_STRIDE);
        uint32_t tag = 0;
        uint32_t file_name_ptr = 0;
        char file_name[32];

        if (!candidate || !readable_range(candidate, 0x30u)) continue;
        if (memory_u32(view, candidate + 0x28u, &tag) &&
            (tag == GUILD_TAG_WGLD || tag == GUILD_TAG_DLGW)) {
            return candidate;
        }

        file_name[0] = 0;
        if (memory_u32(view, candidate + 0x2Cu, &file_name_ptr) &&
            user_address((uintptr_t)file_name_ptr) &&
            memory_ascii(view, (uintptr_t)file_name_ptr, file_name, sizeof(file_name), 24u) &&
            contains_guild_marker(file_name)) {
            return candidate;
        }
    }
    return 0;
}

static int guild_name_from_chain(const MemoryView *view, uint32_t head, uint32_t guild_id,
                                 uint32_t link_offset, char *output, size_t output_size) {
    uint32_t node = head;
    unsigned visited = 0u;
    if (!view || !output || output_size < 2u) return 0;
    output[0] = 0;

    while (user_address((uintptr_t)node) && !(node & 1u) && visited++ < MAX_GUILD_VISITS) {
        uint32_t key = 0, next = 0;
        if (!memory_u32(view, (uintptr_t)node, &key)) return 0;
        if (key == guild_id) {
            if (memory_ascii(view, (uintptr_t)node + 0x1Cu, output, output_size, GUILD_LIMIT) &&
                valid_guild_name(output)) return 1;
            output[0] = 0;
            if (memory_ascii(view, (uintptr_t)node + 0x18u, output, output_size, GUILD_LIMIT) &&
                valid_guild_name(output)) return 1;
            output[0] = 0;
            return 0;
        }
        if (!memory_u32(view, (uintptr_t)node + link_offset, &next) ||
            next == node || !user_address((uintptr_t)next)) {
            return 0;
        }
        node = next;
    }
    return 0;
}

static int resolve_guild_name(const MemoryView *view, uint32_t guild_id,
                              char *output, size_t output_size) {
    uintptr_t cache;
    uint32_t buckets = 0, mask = 0, head = 0;
    uintptr_t bucket_head;
    if (!guild_id || !output || output_size < 2u) return 0;
    output[0] = 0;

    cache = locate_guild_cache(view);
    if (!cache) return 0;
    if (!memory_u32(view, cache + 0x1Cu, &buckets) || !user_address((uintptr_t)buckets)) return 0;
    if (!memory_u32(view, cache + 0x24u, &mask)) return 0;

    bucket_head = (uintptr_t)buckets + (uintptr_t)(guild_id & mask) * 12u + 8u;
    if (!memory_u32(view, bucket_head, &head) || !user_address((uintptr_t)head)) return 0;
    if (guild_name_from_chain(view, head, guild_id, 4u, output, output_size)) return 1;
    return guild_name_from_chain(view, head, guild_id, 8u, output, output_size);
}

static void read_player_guild(const MemoryView *view, uintptr_t player_object,
                              uint32_t descriptors, char *output, size_t output_size) {
    uint32_t guild_id = 0, player_info = 0;
    if (!output || !output_size) return;
    output[0] = 0;

    if (user_address((uintptr_t)descriptors) &&
        memory_u32(view, (uintptr_t)descriptors + PLAYER_GUILD_ID_OFF, &guild_id) && guild_id &&
        resolve_guild_name(view, guild_id, output, output_size)) {
        return;
    }

    output[0] = 0;
    guild_id = 0;
    if (memory_u32(view, player_object + PLAYER_INFO_OFF, &player_info) &&
        user_address((uintptr_t)player_info) &&
        memory_u32(view, (uintptr_t)player_info + PLAYER_INFO_GUILD_KEY_OFF, &guild_id) &&
        guild_id) {
        resolve_guild_name(view, guild_id, output, output_size);
    }
}

static int read_local_player(const MemoryView *view, CharacterSnapshot *snapshot) {
    uint32_t manager = 0, current = 0, initial_first = 0;
    uint64_t wanted_guid = 0;
    unsigned visited = 0u;

    if (!view || !snapshot || !object_manager_pointer(view, &manager)) return 0;
    if (!stable_local_guid(view, manager, &wanted_guid)) return 0;
    if (!memory_u32(view, (uintptr_t)manager + OM_FIRST_OBJECT_OFF, &current) ||
        !user_address((uintptr_t)current)) return 0;
    initial_first = current;

    while (user_address((uintptr_t)current) && !(current & 1u) && visited++ < MAX_OBJECT_VISITS) {
        uint32_t current_first = 0, object_type = 0, descriptors = 0, next = 0;
        uint64_t object_guid = 0;

        if (!memory_u32(view, (uintptr_t)manager + OM_FIRST_OBJECT_OFF, &current_first) ||
            current_first != initial_first) return 0;
        if (!memory_u32(view, (uintptr_t)current + OBJECT_TYPE_OFF, &object_type)) return 0;

        if (object_type == PLAYER_OBJECT_TYPE &&
            memory_u64(view, (uintptr_t)current + OBJECT_GUID_OFF, &object_guid) &&
            object_guid == wanted_guid &&
            memory_u32(view, (uintptr_t)current + OBJECT_DESCRIPTORS_OFF, &descriptors) &&
            user_address((uintptr_t)descriptors)) {
            uint32_t level = 0, bytes0 = 0;
            if (memory_u32(view, (uintptr_t)descriptors + UNIT_LEVEL_OFF, &level) &&
                level >= 1u && level <= 80u) {
                snapshot->level = level;
            }
            if (memory_u32(view, (uintptr_t)descriptors + UNIT_BYTES0_OFF, &bytes0)) {
                snapshot->race_id = bytes0 & 0xFFu;
                snapshot->class_id = (bytes0 >> 8) & 0xFFu;
            }
            read_player_guild(view, (uintptr_t)current, descriptors,
                              snapshot->guild, sizeof(snapshot->guild));
            return 1;
        }

        if (!memory_u32(view, (uintptr_t)current + OBJECT_NEXT_OFF, &next) ||
            next == current || !user_address((uintptr_t)next)) return 0;
        current = next;
    }
    return 0;
}

static void collect_character_snapshot(CharacterSnapshot *snapshot) {
    MemoryView view;
    DWORD now;
    int have_name, have_zone;
    if (!snapshot) return;
    memset(snapshot, 0, sizeof(*snapshot));
    memory_view_init(&view);

    have_name = first_text_match(&view, kPlayerNameLocations, snapshot->name,
                                 sizeof(snapshot->name), NAME_LIMIT, valid_player_name);
    have_zone = first_text_match(&view, kZoneNameLocations, snapshot->zone,
                                 sizeof(snapshot->zone), ZONE_LIMIT, valid_zone_name);
    snapshot->in_world = have_name && have_zone;

    now = GetTickCount();
    if (!snapshot->in_world) {
        gWorldReadySince = 0;
        return;
    }

    if (!gWorldReadySince) gWorldReadySince = now ? now : 1u;
    if ((DWORD)(now - gWorldReadySince) < WORLD_SETTLE_MS) return;
    read_local_player(&view, snapshot);
}

static int game_folder(char *output, size_t output_size) {
    char path[MAX_PATH];
    char *separator;
    size_t length;
    if (!output || output_size < 4u) return 0;
    if (!GetModuleFileNameA(NULL, path, MAX_PATH)) return 0;
    separator = strrchr(path, '\\');
    if (!separator) separator = strrchr(path, '/');
    if (!separator) return 0;
    *separator = 0;
    length = strlen(path);
    if (length + 1u > output_size) return 0;
    memcpy(output, path, length + 1u);
    return 1;
}

static int support_folder(char *output, size_t output_size) {
    char root[MAX_PATH], parent[MAX_PATH];
    int count;
    if (!game_folder(root, sizeof(root))) return 0;
    count = _snprintf(parent, sizeof(parent), "%s\\.modernization_tool", root);
    parent[sizeof(parent) - 1] = 0;
    if (count < 0 || (size_t)count >= sizeof(parent)) return 0;
    CreateDirectoryA(parent, NULL);

    count = _snprintf(output, output_size, "%s\\DiscordPresence", parent);
    if (output_size) output[output_size - 1] = 0;
    if (count < 0 || (size_t)count >= output_size) return 0;
    CreateDirectoryA(output, NULL);
    return 1;
}

static int support_path(char *output, size_t output_size, const char *file_name) {
    char folder[MAX_PATH];
    int count;
    if (!file_name || !support_folder(folder, sizeof(folder))) return 0;
    count = _snprintf(output, output_size, "%s\\%s", folder, file_name);
    if (output_size) output[output_size - 1] = 0;
    return count >= 0 && (size_t)count < output_size;
}

static unsigned load_share_mask(void) {
    char path[MAX_PATH], text[32];
    HANDLE file;
    DWORD read_count = 0;
    char *end = NULL;
    unsigned long value;
    memset(text, 0, sizeof(text));

    if (!support_path(path, sizeof(path), "discord_broadcast_flags")) return SHARE_ALL;
    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                       NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return SHARE_ALL;
    if (!ReadFile(file, text, sizeof(text) - 1u, &read_count, NULL) || !read_count) {
        CloseHandle(file);
        return SHARE_ALL;
    }
    CloseHandle(file);
    text[read_count < sizeof(text) ? read_count : sizeof(text) - 1u] = 0;
    value = strtoul(text, &end, 10);
    if (end == text) return SHARE_ALL;
    return (unsigned)(value & SHARE_ALL);
}

static void json_quote_text(const char *source, char *output, size_t output_size) {
    size_t read_index = 0u, write_index = 0u;
    if (!output || !output_size) return;
    output[0] = 0;

    while (source && source[read_index] && write_index + 1u < output_size) {
        unsigned char ch = (unsigned char)source[read_index++];
        if (ch == '"' || ch == '\\') {
            if (write_index + 2u >= output_size) break;
            output[write_index++] = '\\';
            output[write_index++] = (char)ch;
        } else if (ch >= 32u && ch < 127u) {
            output[write_index++] = (char)ch;
        }
    }
    output[write_index] = 0;
}

static int replace_text_file_atomically(const char *file_name, const char *contents) {
    char destination[MAX_PATH], temporary[MAX_PATH];
    HANDLE file;
    DWORD length, written = 0;
    int count;

    if (!file_name || !contents || !support_path(destination, sizeof(destination), file_name)) return 0;
    count = _snprintf(temporary, sizeof(temporary), "%s.tmp", destination);
    temporary[sizeof(temporary) - 1] = 0;
    if (count < 0 || (size_t)count >= sizeof(temporary)) return 0;

    file = CreateFileA(temporary, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                       FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    length = (DWORD)strlen(contents);
    if (!WriteFile(file, contents, length, &written, NULL) || written != length) {
        CloseHandle(file);
        DeleteFileA(temporary);
        return 0;
    }
    FlushFileBuffers(file);
    CloseHandle(file);

    if (!MoveFileExA(temporary, destination,
                     MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        DeleteFileA(temporary);
        return 0;
    }
    return 1;
}

static void publish_fault_snapshot(void) {
    replace_text_file_atomically(
        "discord_wow_status.json",
        "{\"v\":1,\"ts\":0,\"ok\":false,\"in_world\":false,\"name\":\"\","
        "\"zone\":\"\",\"level\":0,\"faction\":\"\",\"class\":\"\","
        "\"guild\":\"\",\"race\":\"\",\"build\":5875,\"err\":\"fault\"}");
}

static void publish_character_snapshot(void) {
    CharacterSnapshot snapshot;
    unsigned mask;
    char safe_name[NAME_LIMIT * 2u + 8u];
    char safe_zone[ZONE_LIMIT * 2u + 8u];
    char safe_guild[GUILD_LIMIT * 2u + 8u];
    char json[JSON_BUFFER_SIZE];
    const char *race_text, *class_text, *faction_text;

    collect_character_snapshot(&snapshot);
    mask = load_share_mask();
    race_text = snapshot.in_world ? label_for_id(kRaceLabels, snapshot.race_id) : "";
    class_text = (snapshot.in_world && (mask & SHARE_CLASS))
        ? label_for_id(kClassLabels, snapshot.class_id) : "";
    faction_text = (snapshot.in_world && (mask & SHARE_FACTION))
        ? faction_for_race(snapshot.race_id) : "";

    json_quote_text((mask & SHARE_NAME) ? snapshot.name : "", safe_name, sizeof(safe_name));
    json_quote_text((mask & SHARE_ZONE) ? snapshot.zone : "", safe_zone, sizeof(safe_zone));
    json_quote_text((mask & SHARE_GUILD) ? snapshot.guild : "", safe_guild, sizeof(safe_guild));

    _snprintf(
        json, sizeof(json),
        "{\"v\":1,\"ts\":%ld,\"ok\":%s,\"in_world\":%s,"
        "\"name\":\"%s\",\"zone\":\"%s\",\"level\":%u,"
        "\"faction\":\"%s\",\"class\":\"%s\",\"guild\":\"%s\","
        "\"race\":\"%s\",\"build\":5875,\"err\":\"%s\"}",
        (long)time(NULL),
        snapshot.in_world ? "true" : "false",
        snapshot.in_world ? "true" : "false",
        safe_name,
        safe_zone,
        (snapshot.in_world && (mask & SHARE_LEVEL)) ? snapshot.level : 0u,
        faction_text,
        class_text,
        safe_guild,
        race_text,
        snapshot.in_world ? "" : "offsets");
    json[sizeof(json) - 1] = 0;
    replace_text_file_atomically("discord_wow_status.json", json);
}

static int launch_discord_companion(void) {
    char root[MAX_PATH], executable[MAX_PATH], command[MAX_PATH * 2u];
    STARTUPINFOA startup;
    PROCESS_INFORMATION process;
    DWORD attributes;
    int count;

    if (!game_folder(root, sizeof(root))) return 0;
    count = _snprintf(executable, sizeof(executable), "%s\\DiscordPresence.exe", root);
    executable[sizeof(executable) - 1] = 0;
    if (count < 0 || (size_t)count >= sizeof(executable)) return 0;

    attributes = GetFileAttributesA(executable);
    if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_DIRECTORY)) return 0;

    count = _snprintf(command, sizeof(command), "\"%s\" --pid %lu",
                      executable, (unsigned long)GetCurrentProcessId());
    command[sizeof(command) - 1] = 0;
    if (count < 0 || (size_t)count >= sizeof(command)) return 0;

    memset(&startup, 0, sizeof(startup));
    memset(&process, 0, sizeof(process));
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_HIDE;

    if (!CreateProcessA(executable, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, root, &startup, &process)) {
        return 0;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 1;
}

static DWORD WINAPI presence_worker(LPVOID parameter) {
    int companion_running = 0;
    (void)parameter;

    if (WaitForSingleObject(gStopEvent, STARTUP_WAIT_MS) != WAIT_TIMEOUT) return 0;
    do {
#ifdef _MSC_VER
        __try {
            publish_character_snapshot();
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            publish_fault_snapshot();
        }
#else
        publish_character_snapshot();
#endif
        if (!companion_running) companion_running = launch_discord_companion();
    } while (WaitForSingleObject(gStopEvent, SAMPLE_PERIOD_MS) == WAIT_TIMEOUT);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        gStopEvent = CreateEventA(NULL, TRUE, FALSE, NULL);
        if (gStopEvent) gWorkerThread = CreateThread(NULL, 0, presence_worker, NULL, 0, NULL);
    } else if (reason == DLL_PROCESS_DETACH) {
        if (gStopEvent) SetEvent(gStopEvent);
        if (gWorkerThread) {
            WaitForSingleObject(gWorkerThread, 1500u);
            CloseHandle(gWorkerThread);
            gWorkerThread = NULL;
        }
        if (gStopEvent) {
            CloseHandle(gStopEvent);
            gStopEvent = NULL;
        }
    }
    return TRUE;
}
