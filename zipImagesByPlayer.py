import os
import re
import shutil

import string

IMAGE_SUFFIX = ".jpg"
DECKLIST_SUFFIX = ".txt"

DECKLIST_DIRECTORY_ROOT = "./decklists"
ZIP_DECKLIST_DIRECTORY_ROOT = "./zippedDecklists"
ZIP_IMAGE_FILE_DIRECTORY_ROOT = "./zippedImages"

ZIPPED_DECKLISTS_FILE_NAME = "CombinedDecklists"
ZIPPED_IMAGES_FILE_NAME = "CombinedDecklistImages"

IGNORE_PLAYER_NAMES = ["TestCards"]

def prepareZipFileDirectory(directory_root):
	if os.path.isdir(directory_root):
		shutil.rmtree(directory_root)

	os.mkdir(directory_root)

def preparePlayerDirectory(directory_root, player_name):
	player_path = os.path.join(directory_root, player_name)

	if not os.path.isdir(player_path):
		os.mkdir(player_path)

	return player_path

def prepareCombinedDecklists(player_name, format_name):
	combined_decklist_directory_path = preparePlayerDirectory(ZIP_DECKLIST_DIRECTORY_ROOT, player_name)
	combined_decklist_path = os.path.join(combined_decklist_directory_path, player_name + "Combined" + DECKLIST_SUFFIX)
	player_decklist_path = os.path.join(combined_decklist_directory_path, player_name + "_" + format_name + DECKLIST_SUFFIX)

	if not os.path.exists(combined_decklist_path):
		open(combined_decklist_path, "w")

	if not os.path.exists(player_decklist_path):
		open(player_decklist_path, "w")

	return combined_decklist_path, player_decklist_path

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
			print("Copying image files from ", sub_dir)
			player_path = preparePlayerDirectory(ZIP_IMAGE_FILE_DIRECTORY_ROOT, player_name)
			copyImageFilesToDirectory(sub_dir, player_path, files)

def combinePlayerDecklist(source_path, destination_path, files, player_name, format_name):
	for file in files:
		if file.endswith(DECKLIST_SUFFIX):
			with open(os.path.join(source_path, file), "r") as source:
				combined_decklist_path, player_decklist_path = prepareCombinedDecklists(player_name, format_name)
				with open(combined_decklist_path, "a") as dest:
					source_contents = source.read()
					for line in source_contents.split("\n"):
						stripped_line = line.strip()
						if(len(stripped_line)):
							# bit of a hack to remove set codes
							if(stripped_line.endswith(")")):
								stripped_line = stripped_line[:-5]
							dest.write(stripped_line + "\n")
				with open(player_decklist_path, "w") as dest:
					dest.write(source.read())

def copyPlayerDecklistsToZipDirectory():
	for sub_dir, dirs, files in os.walk(DECKLIST_DIRECTORY_ROOT):
		format_name, player_name = getFormatAndPlayerNameFromSubDir(sub_dir)

		if player_name and player_name not in IGNORE_PLAYER_NAMES:
			print("Copying decklists from ", sub_dir)
			player_path = preparePlayerDirectory(ZIP_DECKLIST_DIRECTORY_ROOT, player_name)
			combinePlayerDecklist(sub_dir, player_path, files, player_name, format_name)

def zipDirectory(directory_root, output_file_name):
	print("Zipping directory", directory_root, "to", output_file_name)
	shutil.make_archive(output_file_name, 'zip', directory_root)

# main
prepareZipFileDirectory(ZIP_IMAGE_FILE_DIRECTORY_ROOT)
prepareZipFileDirectory(ZIP_DECKLIST_DIRECTORY_ROOT)
copyPlayerImagesToZipDirectory()
copyPlayerDecklistsToZipDirectory()
zipDirectory(ZIP_IMAGE_FILE_DIRECTORY_ROOT, ZIPPED_IMAGES_FILE_NAME)
zipDirectory(ZIP_DECKLIST_DIRECTORY_ROOT, ZIPPED_DECKLISTS_FILE_NAME)

print("*******************************************************")
print("********************** SUCCESS! ***********************")
print("*******************************************************")