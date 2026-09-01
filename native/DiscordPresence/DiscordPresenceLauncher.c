/*
 * DiscordPresence.exe
 * Invisible companion launcher for Modernization Tool.
 *
 * - is started automatically by DiscordPresence.dll after WoW is running
 * - reads .modernization_tool\DiscordPresence\discord_wow_status.json
 * - publishes Discord Rich Presence over the local Discord IPC named pipe
 * - exits when WoW_Modernized.exe exits
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define STATUS_MAX_AGE 30
#define TICK_MS 2000
#define PIPE_COUNT 10
#define IPC_OPCODE_HANDSHAKE 0u
#define IPC_OPCODE_FRAME 1u
#define DEFAULT_DISCORD_APPLICATION_ID "1544072796098011176"

typedef struct {
    char name[32];
    char zone[80];
    char guild[64];
    char faction[24];
    char class_name[32];
    char race[32];
    int level;
    long long ts;
    int ok;
    int in_world;
} Status;

typedef struct {
    HANDLE pipe;
    char last_activity[768];
    unsigned long nonce;
} DiscordRpc;

static int own_directory(char *out, size_t out_size) {
    char path[MAX_PATH];
    char *slash;
    if (!GetModuleFileNameA(NULL, path, MAX_PATH)) return 0;
    slash = strrchr(path, '\\');
    if (!slash) slash = strrchr(path, '/');
    if (!slash) return 0;
    *slash = 0;
    if (strlen(path) + 1 > out_size) return 0;
    lstrcpynA(out, path, (int)out_size);
    return 1;
}

static int support_directory(char *out, size_t out_size) {
    char root[MAX_PATH], first[MAX_PATH];
    if (!own_directory(root, sizeof(root))) return 0;
    if (strlen(root) + strlen("\\.modernization_tool") + 1 >= sizeof(first)) return 0;
    _snprintf(first, sizeof(first), "%s\\.modernization_tool", root);
    first[sizeof(first) - 1] = 0;
    CreateDirectoryA(first, NULL);
    if (strlen(first) + strlen("\\DiscordPresence") + 1 >= out_size) return 0;
    _snprintf(out, out_size, "%s\\DiscordPresence", first);
    out[out_size - 1] = 0;
    CreateDirectoryA(out, NULL);
    return 1;
}

static int support_file(char *out, size_t out_size, const char *name) {
    char dir[MAX_PATH];
    if (!support_directory(dir, sizeof(dir))) return 0;
    if (strlen(dir) + 1 + strlen(name) + 1 > out_size) return 0;
    _snprintf(out, out_size, "%s\\%s", dir, name);
    out[out_size - 1] = 0;
    return 1;
}

static void log_line(const char *text) {
    char path[MAX_PATH];
    HANDLE file;
    DWORD written;
    SYSTEMTIME st;
    char line[1200];
    if (!support_file(path, sizeof(path), "DiscordPresence.log")) return;
    file = CreateFileA(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                       NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return;
    GetLocalTime(&st);
    _snprintf(line, sizeof(line), "%04u-%02u-%02u %02u:%02u:%02u %s\r\n",
              st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond,
              text ? text : "");
    line[sizeof(line) - 1] = 0;
    WriteFile(file, line, (DWORD)strlen(line), &written, NULL);
    CloseHandle(file);
}

static int read_text_file(const char *path, char *out, size_t out_size) {
    HANDLE file;
    DWORD got = 0;
    if (!out || out_size < 2) return 0;
    out[0] = 0;
    file = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                       NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return 0;
    if (!ReadFile(file, out, (DWORD)(out_size - 1), &got, NULL)) {
        CloseHandle(file);
        return 0;
    }
    CloseHandle(file);
    out[got] = 0;
    return 1;
}

static void trim_ascii(char *text) {
    char *start, *end;
    if (!text) return;
    start = text;
    while (*start == ' ' || *start == '\t' || *start == '\r' || *start == '\n') ++start;
    if (start != text) memmove(text, start, strlen(start) + 1);
    end = text + strlen(text);
    while (end > text && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\r' || end[-1] == '\n'))
        --end;
    *end = 0;
}

static int valid_application_id(const char *text) {
    size_t i, n;
    if (!text) return 0;
    n = strlen(text);
    if (n < 15 || n > 24) return 0;
    for (i = 0; i < n; ++i)
        if (text[i] < '0' || text[i] > '9') return 0;
    return 1;
}

static int load_application_id(char *out, size_t out_size) {
    char path[MAX_PATH];
    char override_id[64] = {0};

    if (!out || out_size <= strlen(DEFAULT_DISCORD_APPLICATION_ID)) return 0;
    lstrcpynA(out, DEFAULT_DISCORD_APPLICATION_ID, (int)out_size);

    /* Optional advanced override. Normal users never need this file. */
    if (support_file(path, sizeof(path), "discord_application_id") &&
        read_text_file(path, override_id, sizeof(override_id))) {
        trim_ascii(override_id);
        if (valid_application_id(override_id)) {
            lstrcpynA(out, override_id, (int)out_size);
        } else if (override_id[0]) {
            log_line("Ignoring invalid discord_application_id override; using built-in OctoWoW ID.");
        }
    }

    return valid_application_id(out);
}

static DWORD parse_target_pid(const char *cmdline) {
    const char *p;
    char *end = NULL;
    unsigned long value;

    if (!cmdline) return 0;
    p = strstr(cmdline, "--pid");
    if (!p) return 0;
    p += 5;
    while (*p == ' ' || *p == '\t') ++p;
    if (!*p) return 0;

    value = strtoul(p, &end, 10);
    if (end == p || value == 0 || value > 0xFFFFFFFFul) return 0;
    return (DWORD)value;
}

static DWORD find_process(const char *exe_name) {
    HANDLE snapshot;
    PROCESSENTRY32 entry;
    DWORD pid = 0;
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    memset(&entry, 0, sizeof(entry));
    entry.dwSize = sizeof(entry);
    if (Process32First(snapshot, &entry)) {
        do {
            if (_stricmp(entry.szExeFile, exe_name) == 0) {
                pid = entry.th32ProcessID;
                break;
            }
        } while (Process32Next(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return pid;
}

static const char *find_key(const char *json, const char *key) {
    static char pattern[80];
    const char *p;
    _snprintf(pattern, sizeof(pattern), "\"%s\":", key);
    pattern[sizeof(pattern) - 1] = 0;
    p = strstr(json, pattern);
    return p ? p + strlen(pattern) : NULL;
}

static int json_bool(const char *json, const char *key, int *value) {
    const char *p = find_key(json, key);
    if (!p || !value) return 0;
    while (*p == ' ' || *p == '\t') ++p;
    if (strncmp(p, "true", 4) == 0) { *value = 1; return 1; }
    if (strncmp(p, "false", 5) == 0) { *value = 0; return 1; }
    return 0;
}

static int json_int64(const char *json, const char *key, long long *value) {
    const char *p = find_key(json, key);
    char *end = NULL;
    long long v;
    if (!p || !value) return 0;
    v = _strtoi64(p, &end, 10);
    if (end == p) return 0;
    *value = v;
    return 1;
}

static int json_int(const char *json, const char *key, int *value) {
    long long v = 0;
    if (!json_int64(json, key, &v)) return 0;
    *value = (int)v;
    return 1;
}

static int json_string(const char *json, const char *key, char *out, size_t out_size) {
    const char *p = find_key(json, key);
    size_t w = 0;
    if (!p || !out || out_size < 2) return 0;
    while (*p == ' ' || *p == '\t') ++p;
    if (*p++ != '"') return 0;
    while (*p && *p != '"' && w + 1 < out_size) {
        if (*p == '\\') {
            ++p;
            if (!*p) break;
            if (*p == '"' || *p == '\\' || *p == '/') out[w++] = *p++;
            else if (*p == 'n') { out[w++] = '\n'; ++p; }
            else if (*p == 'r') { out[w++] = '\r'; ++p; }
            else if (*p == 't') { out[w++] = '\t'; ++p; }
            else return 0;
        } else {
            out[w++] = *p++;
        }
    }
    out[w] = 0;
    return *p == '"';
}

static int load_status(Status *status) {
    char path[MAX_PATH], json[2048];
    time_t now;
    memset(status, 0, sizeof(*status));
    if (!support_file(path, sizeof(path), "discord_wow_status.json")) return 0;
    if (!read_text_file(path, json, sizeof(json))) return 0;
    if (!json_bool(json, "ok", &status->ok) ||
        !json_bool(json, "in_world", &status->in_world) ||
        !json_int64(json, "ts", &status->ts))
        return 0;
    now = time(NULL);
    if (!status->ok || !status->in_world ||
        status->ts <= 0 || (long long)now - status->ts > STATUS_MAX_AGE ||
        status->ts - (long long)now > 5)
        return 0;
    json_string(json, "name", status->name, sizeof(status->name));
    json_string(json, "zone", status->zone, sizeof(status->zone));
    json_string(json, "guild", status->guild, sizeof(status->guild));
    json_string(json, "faction", status->faction, sizeof(status->faction));
    json_string(json, "class", status->class_name, sizeof(status->class_name));
    json_string(json, "race", status->race, sizeof(status->race));
    json_int(json, "level", &status->level);
    return status->name[0] || status->zone[0] || status->level > 0;
}

static int rpc_read_packet(HANDLE pipe, char *payload, size_t payload_size) {
    uint32_t header[2];
    DWORD got = 0, total = 0;
    if (!ReadFile(pipe, header, sizeof(header), &got, NULL) || got != sizeof(header)) return 0;
    if (header[1] >= payload_size) return 0;
    while (total < header[1]) {
        DWORD chunk = 0;
        if (!ReadFile(pipe, payload + total, header[1] - total, &chunk, NULL) || chunk == 0)
            return 0;
        total += chunk;
    }
    payload[total] = 0;
    return 1;
}

static int rpc_write_packet(HANDLE pipe, uint32_t opcode, const char *json) {
    unsigned char buffer[2048];
    uint32_t *header = (uint32_t *)buffer;
    DWORD written = 0;
    size_t len = strlen(json);
    if (len + 8 > sizeof(buffer)) return 0;
    header[0] = opcode;
    header[1] = (uint32_t)len;
    memcpy(buffer + 8, json, len);
    return WriteFile(pipe, buffer, (DWORD)(len + 8), &written, NULL) &&
           written == (DWORD)(len + 8);
}

static void rpc_close(DiscordRpc *rpc) {
    if (rpc->pipe && rpc->pipe != INVALID_HANDLE_VALUE) CloseHandle(rpc->pipe);
    rpc->pipe = INVALID_HANDLE_VALUE;
    rpc->last_activity[0] = 0;
}

static int rpc_connect(DiscordRpc *rpc, const char *application_id) {
    int i;
    char pipe_name[64], handshake[160], response[2048];
    rpc_close(rpc);
    for (i = 0; i < PIPE_COUNT; ++i) {
        _snprintf(pipe_name, sizeof(pipe_name), "\\\\.\\pipe\\discord-ipc-%d", i);
        rpc->pipe = CreateFileA(pipe_name, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                                OPEN_EXISTING, 0, NULL);
        if (rpc->pipe != INVALID_HANDLE_VALUE) break;
    }
    if (rpc->pipe == INVALID_HANDLE_VALUE) return 0;
    _snprintf(handshake, sizeof(handshake), "{\"v\":1,\"client_id\":\"%s\"}", application_id);
    if (!rpc_write_packet(rpc->pipe, IPC_OPCODE_HANDSHAKE, handshake) ||
        !rpc_read_packet(rpc->pipe, response, sizeof(response)) ||
        (!strstr(response, "\"READY\"") && !strstr(response, "\"evt\":\"READY\""))) {
        rpc_close(rpc);
        return 0;
    }
    log_line("Connected to Discord IPC.");
    return 1;
}

static void title_case_faction(char *text) {
    if (text && text[0] >= 'a' && text[0] <= 'z') text[0] = (char)(text[0] - 'a' + 'A');
}

static void format_activity(const Status *s, char *out, size_t out_size) {
    char details[384] = {0};
    char extra[192] = {0};
    char faction[24] = {0};
    if (s->faction[0]) {
        lstrcpynA(faction, s->faction, sizeof(faction));
        title_case_faction(faction);
    }

    if (s->name[0] && s->guild[0])
        _snprintf(details, sizeof(details), "%s <%s>", s->name, s->guild);
    else if (s->name[0])
        _snprintf(details, sizeof(details), "%s", s->name);
    else if (s->guild[0])
        _snprintf(details, sizeof(details), "<%s>", s->guild);

    if (s->level > 0 && s->class_name[0])
        _snprintf(extra, sizeof(extra), "Lvl %d %s", s->level, s->class_name);
    else if (s->level > 0)
        _snprintf(extra, sizeof(extra), "Lvl %d", s->level);
    else if (s->class_name[0])
        _snprintf(extra, sizeof(extra), "%s", s->class_name);

    if (s->race[0]) {
        size_t used = strlen(extra);
        if (used)
            _snprintf(extra + used, sizeof(extra) - used, " \\u00b7 %s", s->race);
        else
            _snprintf(extra, sizeof(extra), "%s", s->race);
    }

    if (faction[0]) {
        size_t used = strlen(extra);
        if (used)
            _snprintf(extra + used, sizeof(extra) - used, " \\u00b7 %s", faction);
        else
            _snprintf(extra, sizeof(extra), "%s", faction);
    }

    if (details[0] && extra[0]) {
        size_t used = strlen(details);
        _snprintf(details + used, sizeof(details) - used, " \\u00b7 %s", extra);
    } else if (!details[0] && extra[0]) {
        lstrcpynA(details, extra, sizeof(details));
    }

    _snprintf(out, out_size,
              "{\"details\":\"%s\",\"state\":\"%s\"}",
              details, s->zone);
    out[out_size - 1] = 0;
}

static int rpc_set_activity(DiscordRpc *rpc, DWORD pid, const char *activity_json) {
    char command[1400], response[2048];
    if (!rpc || rpc->pipe == INVALID_HANDLE_VALUE) return 0;
    if (strcmp(rpc->last_activity, activity_json) == 0) return 1;
    ++rpc->nonce;
    _snprintf(command, sizeof(command),
              "{\"cmd\":\"SET_ACTIVITY\",\"args\":{\"pid\":%lu,\"activity\":%s},"
              "\"nonce\":\"%lu\"}",
              (unsigned long)pid, activity_json, rpc->nonce);
    command[sizeof(command) - 1] = 0;
    if (!rpc_write_packet(rpc->pipe, IPC_OPCODE_FRAME, command) ||
        !rpc_read_packet(rpc->pipe, response, sizeof(response))) {
        rpc_close(rpc);
        return 0;
    }
    if (strstr(response, "\"ERROR\"")) {
        log_line(response);
        return 0;
    }
    lstrcpynA(rpc->last_activity, activity_json, sizeof(rpc->last_activity));
    return 1;
}

static void rpc_clear(DiscordRpc *rpc, DWORD pid) {
    char command[256], response[1024];
    if (!rpc || rpc->pipe == INVALID_HANDLE_VALUE) return;
    ++rpc->nonce;
    _snprintf(command, sizeof(command),
              "{\"cmd\":\"SET_ACTIVITY\",\"args\":{\"pid\":%lu,\"activity\":null},"
              "\"nonce\":\"%lu\"}",
              (unsigned long)pid, rpc->nonce);
    rpc_write_packet(rpc->pipe, IPC_OPCODE_FRAME, command);
    rpc_read_packet(rpc->pipe, response, sizeof(response));
}

int WINAPI WinMain(HINSTANCE instance, HINSTANCE prev, LPSTR cmdline, int show) {
    char application_id[64] = {0};
    DiscordRpc rpc;
    HANDLE wow_process = NULL;
    DWORD pid = 0;
    DWORD requested_pid = 0;
    int have_id;
    int wait_loops = 0;
    (void)instance; (void)prev; (void)show;

    memset(&rpc, 0, sizeof(rpc));
    rpc.pipe = INVALID_HANDLE_VALUE;
    rpc.nonce = (unsigned long)GetTickCount();

    have_id = load_application_id(application_id, sizeof(application_id));
    if (!have_id) {
        log_line("Built-in Discord Application ID is invalid; presence is disabled.");
    }

    /* Normal path: DiscordPresence.dll passes the exact WoW process id.
     * The name scan remains only as a harmless manual/debug fallback. */
    requested_pid = parse_target_pid(cmdline);
    pid = requested_pid;

    while (!pid && wait_loops++ < 25) {
        pid = find_process("WoW_Modernized.exe");
        if (!pid) Sleep(200);
    }
    if (!pid) {
        log_line("No running WoW_Modernized.exe found; DiscordPresence exiting.");
        return 0;
    }

    wow_process = OpenProcess(SYNCHRONIZE, FALSE, pid);
    if (!wow_process) {
        log_line("Could not open the target WoW process; DiscordPresence exiting.");
        return 0;
    }

    log_line("WoW_Modernized.exe detected.");

    while (WaitForSingleObject(wow_process, 0) == WAIT_TIMEOUT) {
        Status status;
        char activity[768];

        if (have_id && rpc.pipe == INVALID_HANDLE_VALUE)
            rpc_connect(&rpc, application_id);

        if (have_id && rpc.pipe != INVALID_HANDLE_VALUE) {
            if (load_status(&status)) {
                format_activity(&status, activity, sizeof(activity));
                rpc_set_activity(&rpc, pid, activity);
            } else {
                /* Keep only the Discord application header while the game is
                 * loading, on character select, or when the snapshot is stale.
                 * This also prevents old character/zone text from lingering. */
                rpc_set_activity(&rpc, pid, "{}");
            }
        }
        Sleep(TICK_MS);
    }

    if (rpc.pipe != INVALID_HANDLE_VALUE) {
        rpc_clear(&rpc, pid);
        rpc_close(&rpc);
    }
    CloseHandle(wow_process);
    log_line("WoW stopped; DiscordPresence exiting.");
    return 0;
}
