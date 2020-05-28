/*
 * Clean deepracer directory recursively.
 * This utility was made to avoid entering sudo password every time
 * you want to clean your data.
 *
 * To build: gcc -o delete-last delete-last.c
 * To run:
 * 	sudo chown root:<YOUR_GID> delete-last
 * 	sudo chmod 4750 delete-last
 * 	./delete-last
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <dirent.h>
#include <errno.h>
#include <string.h>

int filter(const struct dirent *entry, const unsigned char type) {
	if (entry->d_type == type)
		return strcmp(entry->d_name, ".") && strcmp(entry->d_name, "..");
	else
		return 0;
}

int filtdir(const struct dirent *entry) {
	return filter(entry, DT_DIR);
}

int filtreg(const struct dirent *entry) {
	return filter(entry, DT_REG);
}

void deletedir(const char* path) {
	char full[512];
	int ret;
	struct dirent **dirlist, **filelist;
	int d, f;
	d = scandir(path, &dirlist, filtdir, NULL);
	f = scandir(path, &filelist, filtreg, NULL);

	printf("Deleting %s\n", path);

	if (!strcmp(path, "/")) {
		printf("Error: remove filesystem root attempt!\n");
		exit(EXIT_FAILURE);
	}
	if (d < 0 || f < 0) {
		perror("Failed to read directory");
		exit(EXIT_FAILURE);
	}

	while (d--) {
		strcpy(full, path);
		strcat(full, "/");
		strcat(full, dirlist[d]->d_name);
		deletedir(full);
		ret = remove(full);
		if (ret < 0)
			perror("Failed to remove");
		free(dirlist[d]);
	}
	while (f--) {
		strcpy(full, path);
		strcat(full, "/");
		strcat(full, filelist[f]->d_name);
		ret = remove(full);
		if (ret < 0)
			perror("Failed to remove");
		free(filelist[f]);
	}

	free(dirlist);
	free(filelist);
}

int main() {
	// path should be hardcoded
	// we do not want root privileged program deleting all our stuff
	const char* path = "/<YOUR_PATH>/deepracer-local/";
	char* sub[2];
	char full[512];
	int ret;
	// set subpaths
	sub[0] = "data/robomaker";
	sub[1] = "data/minio/bucket/current";

	// set UID to root
	ret = setuid(0);
	if (ret < 0) {
		perror("Failed to grant root privileges");
		exit(EXIT_FAILURE);
	}

	for (int i = 0; i < 2; i++) {
		strcpy(full, path);
		strcat(full, sub[i]);
		deletedir(full);
	}

	return ret;
}

