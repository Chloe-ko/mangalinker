import os
import re
import sqlite3
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import sys
from contextlib import contextmanager
from dotenv import load_dotenv
from pathlib import Path

# Logger setup
def get_logger(name):
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if os.getenv('DEBUG', False) else logging.INFO)  # Set the logging level

    # Create a handler that writes log messages to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if os.getenv('DEBUG', False) else logging.INFO)  # Set the logging level for the handler

    # Create a formatter that specifies the format of log messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add the formatter to the handler
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger

# load env variables
load_dotenv()

logger = get_logger('mangawatcher')

@contextmanager
def get_db_connection(db_path):
    connection = sqlite3.connect(db_path)
    try:
        yield connection
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        connection.close()

# Database setup
logger.info("Setting up database")
with get_db_connection('file_mappings.db') as conn:
    c = conn.cursor()
    logger.info("Running database migrations")
    c.execute('''
        CREATE TABLE IF NOT EXISTS mappings (
            source_filename TEXT PRIMARY KEY,
            target_filename TEXT
        )
    ''')
    conn.commit()
    c.close()

# Define the source and target directories
source_directory = os.getenv('SOURCE_PATH')
target_directory = os.getenv('TARGET_PATH')

if not source_directory:
    logger.fatal("SOURCE_PATH environment variable not set")
    exit(1)

source_path = Path(source_directory)
if not source_path.exists():
    logger.fatal(f"Source path does not exist: {source_directory}")
    exit(1)
if not source_path.is_dir():
    logger.fatal(f"Source path is not a directory: {source_directory}")
    exit(1)

if not target_directory:
    logger.fatal("TARGET_PATH environment variable not set")
    exit(1)
    
target_path = Path(target_directory)
if not target_path.exists():
    logger.fatal(f"Target path does not exist: {target_directory}")
    exit(1)
if not target_path.is_dir():
    logger.fatal(f"Target path is not a directory: {target_directory}")
    exit(1)

# Patterns for chapter and volume parsing
explicit_patterns = [
    r'ch[ .\-_]*(\d+)([ .\-_]*(part|p|pt)[ .\-_]*(\d+))?(\.\d+)?',
    r'chapter[ .\-_]*(\d+)([ .\-_]*(part|p|pt)[ .\-_]*(\d+))?(\.\d+)?',
    r'c[ .\-_]*(\d+)([ .\-_]*(part|p|pt)[ .\-_]*(\d+))?(\.\d+)?',
    r'chap[ .\-_]*(\d+)([ .\-_]*(part|p|pt)[ .\-_]*(\d+))?(\.\d+)?'
]

implicit_patterns = [
    r'(\d+)([ .\-_]*(part|p|pt)[ .\-_]*)(\d+)(\.\d+)?',
    r'(\d+)([._-]\d+)?(?=\.\w+$)',
    r'(\d+)([,.+\-_]\d+)?'
]

volume_indicators = ['v', 'vol', 'volume']

def get_chapter(filename, patterns):
    filename = filename.replace(" ", "").lower()
    original_filename = filename  # Keep a copy of the original filename

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            if pattern in implicit_patterns:
                # Extract the substring before the matched number
                pre_match_substring = filename[:match.start()].rstrip('.,-_+')

                # Check if the substring ends with a volume indicator
                if any(pre_match_substring.endswith(indicator) for indicator in volume_indicators):
                    continue  # Skip if it's a volume indicator
                
                chapter_number = match.group(1)
                part_number = match.group(4) if len(match.groups()) >= 4 else match.group(2)
                if part_number:
                    part_number = part_number.lstrip('._-')
                chapter_part = f"{chapter_number}.{part_number}" if part_number else str(chapter_number)
            else:
                chapter_number = match.group(1)
                part_number = match.group(4) or match.group(5)
                if part_number:
                    part_number = part_number.lstrip('.')
                chapter_part = f"{chapter_number}.{part_number}" if part_number else str(chapter_number)

            # If the matched part is at the start of the filename   
            if match.start() == 0:
                leftover_filename = filename[match.end():]
            elif match.end() == len(filename):
                leftover_filename = filename[:match.start()]
            else:
                leftover_filename = filename[:match.start()] + filename[match.end():]
            
            return chapter_part, leftover_filename

    return None, original_filename

def get_volume(filename):
    volume_pattern = r'(v|vol|volume)[ .\-_:]*(\d+)'
    match = re.search(volume_pattern, filename, re.IGNORECASE)
    if match:
        return str(match.group(2))
    return None

patterns = explicit_patterns + implicit_patterns

def process_file(source_file_path):
    filename = os.path.basename(source_file_path)
    subfolder_name = os.path.basename(os.path.dirname(source_file_path))
    logger.info(f"Processing new file: {subfolder_name}/{filename}")
    chapter, modified_filename = get_chapter(filename, patterns)
    volume = get_volume(modified_filename)

    target_subfolder_path = os.path.join(target_directory, subfolder_name)
    Path(target_subfolder_path).mkdir(parents=True, exist_ok=True)

    target_filename = f"{subfolder_name} Chapter {chapter}"
    if volume:
        target_filename += f" (Volume {volume})"
    target_filename += os.path.splitext(filename)[1]

    target_file_path = os.path.join(target_subfolder_path, target_filename)
    try:
        os.link(source_file_path, target_file_path)
    except FileExistsError:
        logger.warning(f"File already exists: {target_file_path}")
    # Add the mapping to the database
    with get_db_connection('file_mappings.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO mappings (source_filename, target_filename) VALUES (?, ?)', (source_file_path, target_file_path))
        conn.commit()
        c.close()

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_file(event.src_path)
def maintenance():
    logger.info("Running maintenance")

    # Retrieve all mappings from the database
    with get_db_connection('file_mappings.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM mappings')
        mappings = c.fetchall()
        c.close()

    for source_filename, target_filename in mappings:
        source_exists = Path(source_filename).exists()
        target_exists = Path(target_filename).exists()

        # If the source file exists but the target file does not
        if source_exists and not target_exists:
            logger.info(f"Re-creating hardlink for {source_filename}")
            target_subfolder_path = Path(target_filename).parent
            target_subfolder_path.mkdir(parents=True, exist_ok=True)
            try:
                os.link(source_filename, target_filename)
            except FileExistsError:
                logger.warning(f"File already exists: {target_filename}")

        # If neither the source file nor the target file exists
        elif not source_exists and not target_exists:
            logger.info(f"Removing mapping for missing file: {source_filename}")
            with get_db_connection('file_mappings.db') as conn:
                c = conn.cursor()
                c.execute('DELETE FROM mappings WHERE source_filename=?', (source_filename,))
                conn.commit()
                c.close()
                
def scan_directory():
    logger.info("Running scheduled scan")
    for root, dirs, files in os.walk(source_directory):
        logger.debug(f"Scanning directory: {root}")
        logger.debug(f"Found directories: {dirs}")
        logger.debug(f"Found files: {files}")
        for file in files:
            logger.debug(f"Found file: {file}")
            file_path = os.path.join(root, file)
            with get_db_connection('file_mappings.db') as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM mappings WHERE source_filename=?', (file_path,))
                if not c.fetchone():
                    process_file(file_path)
                conn.commit()
                c.close()

observer = Observer()
event_handler = MyHandler()
observer.schedule(event_handler, path=source_directory, recursive=True)
logger.info("Starting observer")
observer.start()

try:
    while True:
        maintenance()  # Call the maintenance function
        scan_directory()
        time.sleep(os.getenv('SCAN_INTERVAL_SECONDS', 3600))  # Hourly scan
except KeyboardInterrupt:
    observer.stop()
observer.join()