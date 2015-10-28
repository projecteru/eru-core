#include <sys/stat.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>

#define PRINT(fmt, ...) do{ fprintf(stdout, fmt, __VA_ARGS__); fflush(stdout); } while(0)
#define SLEEP() usleep(500)
#define LENS(x) (sizeof(x) / sizeof((x)[0]))
#define STRING_ARRAY_CONCAT(A, An, B, Bn) \
  (char **)string_array_concat((const void *)(A), (An), (const void *)(B), (Bn));

#define INTERFACE_ENV "NBE_VETHS"
#define VETH_PREFIX "vnbe"
#define NAME_ENV "APPNAME"

char *string_array_concat(const void *a, size_t an, const void *b, size_t bn) {
    size_t s = sizeof(char *);
    char *p = malloc(s * (an + bn));
    memcpy(p, a, an*s);
    memcpy(p + an*s, b, bn*s);
    return p;
}

int starts_with(const char *pre, const char *str)
{
    size_t lenpre = strlen(pre);
    size_t lenstr = strlen(str);
    return lenstr < lenpre ? 0 : strncmp(pre, str, lenpre) == 0;
}

void set_params(const char *path, const char *value) {
    FILE *fp;
    fp = fopen(path, "w");
    if (fp == NULL) {
        PRINT("%s\n", "Open file failed");
        return;
    }
    fprintf(fp, "%s", value);
    fclose(fp);
}

int check_interface_up(const char *interface) {
    struct ifreq ifr;
    int sock = socket(PF_INET6, SOCK_DGRAM, IPPROTO_IP);
    memset(&ifr, 0, sizeof(ifr));
    strcpy(ifr.ifr_name, interface);
    if (ioctl(sock, SIOCGIFFLAGS, &ifr) < 0) {
        perror("SIOCGIFFLAGS");
        close(sock);
        return -1;
    }
    close(sock);
    return !!(ifr.ifr_flags & IFF_UP);
}

void wait_for_veths(char *interfaces) {
    if (interfaces == NULL) {
        return;
    }
    char *veth;
    while ((veth = strsep(&interfaces, ";"))) {
        if (!starts_with(VETH_PREFIX, veth)) {
            continue;
        }
        PRINT("Wait %s...", veth);
        while (!check_interface_up(veth)) SLEEP();
        PRINT("Done%s", "\n");
    }
}

void exec_new_process(int argc, char **argv, char *user) {
    if (user == NULL) {
        PRINT("%s\n", "No user");
        return;
    }
    char *vars[4] = {"sudo", "-E", "-u", user};
    char **s = STRING_ARRAY_CONCAT(vars, 4, argv + 1, argc - 1);
    execvp("sudo", s);
    free(s);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        PRINT("%s\n", "No params");
        exit(0);
    }
    set_params("/writable-proc/sys/net/core/somaxconn", "32768");
    set_params("/writable-proc/sys/net/core/somaxconn", "32768");
    chmod("/dev/stdout", 0777);
    chmod("/dev/stderr", 0777);
    wait_for_veths(getenv(INTERFACE_ENV));
    exec_new_process(argc, argv, getenv(NAME_ENV));
    return 0;
}
