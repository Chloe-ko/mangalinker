# mangalinker
Hard links manga files from one folder to another for better naming convention

I'm too lazy to make a proper README
If you know Docker, this is easy to run.

AI Generated TL;DR:
Mangalinker is a Python-based application designed to monitor a specified directory for new manga files, process them according to predefined patterns, and organize them into a target directory. It also maintains a database of file mappings for easy management.

The following ENV variables are available:

SOURCE_PATH - The path to the source directory where the manga files are located.

TARGET_PATH - The path to the target directory where processed files will be hardlinked to.

Important: Target and Source path need to be mounted by the same docker volume, in order to appear like being on the same disk inside the container. Otherwise, hardlinking won't work.

DEBUG - Set to True to enable debug logging. Defaults to False.
SCAN_INTERVAL_SECONDS - The interval in seconds for the maintenance and directory scan operations. Defaults to 3600 (1 hour).

Example:

```
docker run -d \
  -e SOURCE_PATH=/media/source \
  -e TARGET_PATH=/media/target \
  -v /path/to/media:/media \
  neneya:mangalinker
```
