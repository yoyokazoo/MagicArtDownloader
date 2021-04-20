import os
import re
import shutil

import string

IMAGE_SUFFIX = ".jpg"
DECKLIST_SUFFIX = ".txt"

DECKLIST_DIRECTORY_ROOT = "./decklists"
ZIP_FILE_DIRECTORY_ROOT = "./zipped"

ZIPPED_FILE_NAME = "DecklistImages"

IGNORE_PLAYER_NAMES = ["TestCards"]

def prepareZipFileDirectory():
	if os.path.isdir(ZIP_FILE_DIRECTORY_ROOT):
		shutil.rmtree(ZIP_FILE_DIRECTORY_ROOT)

	os.mkdir(ZIP_FILE_DIRECTORY_ROOT)

def preparePlayerDirectory(player_name):
	player_path = os.path.join(ZIP_FILE_DIRECTORY_ROOT, player_name)

	if not os.path.isdir(player_path):
		os.mkdir(player_path)

	return player_path

def getFormatAndPlayerNameFromSubDir(sub_dir):
	sub_dir = sub_dir.replace('\\', '/')
	format_name_matches = re.search("\.\/decklists\/(.*?)\/(.*?)(\/|$)", sub_dir)
	format_name = format_name_matches.group(1) if format_name_matches else ""
	player_name = format_name_matches.group(2) if format_name_matches else ""
	return format_name, player_name

def copyImageFilesToDirectory(source_path, destination_path, files):
	for file in files:
		if file.endswith(IMAGE_SUFFIX):
			shutil.copy(os.path.join(source_path, file), os.path.join(destination_path, file))

def copyPlayerImagesToZipDirectory():
	for sub_dir, dirs, files in os.walk(DECKLIST_DIRECTORY_ROOT):
		format_name, player_name = getFormatAndPlayerNameFromSubDir(sub_dir)

		if player_name and player_name not in IGNORE_PLAYER_NAMES:
			print("Copying image files from", sub_dir)
			player_path = preparePlayerDirectory(player_name)
			copyImageFilesToDirectory(sub_dir, player_path, files)

def zipImageDirectory():
	print("Zipping directory", ZIP_FILE_DIRECTORY_ROOT, "to", ZIPPED_FILE_NAME)
	shutil.make_archive(ZIPPED_FILE_NAME, 'zip', ZIP_FILE_DIRECTORY_ROOT)

# main
prepareZipFileDirectory()
copyPlayerImagesToZipDirectory()
zipImageDirectory()

print("*******************************************************")
print("********************** SUCCESS! ***********************")
print("*******************************************************")