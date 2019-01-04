"""Silence Remover
   Remove the silence from songs and normalise the volume.
   Author: Samuel Pell
   Date: 02/01/19 (DD/MM/YY)

   Run me with:
       python .\silence_cutter.py

   NB: Built and tested on windows, results may vary on non-windows platforms.
"""
from pydub import AudioSegment
from pydub.silence import split_on_silence
from pydub.utils import mediainfo
from glob import glob
import multiprocessing
import os
import shutil

## PARAMETERS ##
#REMINDER: dB values SHOULD be negative
SILENCE_CUTOFF = 2500 #ms - when do we start cutting silence
THRESHOLD = -35 #dB - value at which song is considered silent
ACCEPTABLE_SILENCE = 2000 #ms - how much silence do we want to leave between songs
TARGET_VOLUME = -15 #dB

OUTPUT_FORMAT = "mp3"
DEST_DIR = "./output/" # Folder to put cleaned items in
OUTPUT_NAME_FORMAT = "{}{} - cleaned.{}".format(DEST_DIR, "{}", OUTPUT_FORMAT)

DESIRED_THREADS = 6 #how many threads to use for parallelisation


def pool_size():
    """How large should we make our pool?"""
    if DESIRED_THREADS > 1:
        return min(DESIRED_THREADS, multiprocessing.cpu_count())
    else:
        raise Exception("ARG ERROR: DESIRED_THREADS is not valid")


def make_output_dir(directory):
    """Make a new, clean output directory to dump output to."""
    if os.path.exists(directory):
        try:
            shutil.rmtree(directory)
        except OSError:
            print("[SETUP] ERROR: Removing the existing output directory failed")
            return False
        else:
            print("[SETUP] STATUS: Existing output directory removed")

    try:
        os.mkdir(directory)
    except OSError:
        print("[SETUP] ERROR: Creation of the output directory failed")
        return False
    else:
        print("[SETUP] STATUS: Successfully created output directory")
        return True


def match_target_amplitude(audio, target_volume):
    """Amplify quiet songs up to the target volume."""
    if audio.dBFS < target_volume:
        required_gain = target_volume - audio.dBFS
        return audio.apply_gain(required_gain)
    else:
        return audio


def cut_and_eq(song_name):
    """Cut out silence from the beginning/end of a song and amplify the song if
       necessary. Returns None on success and the name of the song on failure."""
    print("[{}] STATUS: Loading...".format(song_name))
    sound_file = AudioSegment.from_mp3(song_name)
    print("[{}] STATUS: Loaded, now processing...".format(song_name))
    sound_file = match_target_amplitude(sound_file, TARGET_VOLUME) # Amplify beforehand to prevent over-zealous cutting
    chunks = split_on_silence(sound_file, SILENCE_CUTOFF, THRESHOLD, keep_silence=ACCEPTABLE_SILENCE)

    if len(chunks) > 1:
        print("[{}] ERROR: Too many chunks ({}) cannot export".format(song_name, len(chunks)))
        return song_name
    else:
        output = AudioSegment.empty()
        for chunk in chunks:
            output += chunk

        new_name = song_name.split(".")[0]
        print("[{}] STATUS: Processed, now exporting...".format(song_name))
        metadata = mediainfo(song_name).get('TAG',{})
        output.export(OUTPUT_NAME_FORMAT.format(new_name), format=OUTPUT_FORMAT, tags=metadata)
        print("[{}] STATUS: Exported to {} - cleaned.{}".format(song_name, new_name, OUTPUT_FORMAT))
        return None


def process_songs(songs):
    """Process the songs using the a parallised pool. Returns the list of
       failed songs."""
    print("[SETUP] STATUS: Creating the pool.")
    workers = multiprocessing.Pool(pool_size())
    print("[SETUP] STATUS: Pool created with {} workers, assigning work.".format(pool_size()))
    results = workers.map(cut_and_eq, songs)
    workers.close()
    workers.join()

    results = [result for result in results if result is not None]
    return results


def main():
    """Main section of the program."""
    print("[SETUP] STATUS: Loading song list")
    songs = glob("*.mp3") #get the list of songs to operate on

    print("[SETUP] STATUS: Creating output directory...")
    if not make_output_dir(DEST_DIR):
        return False
    else:
        failures = process_songs(songs)
        print("[DONE] STATUS: All files processed")
        if len(failures) > 0:
            percent_failed = len(failures) / len(songs) * 100
            print("[DONE] STATUS: There were {} failures ({}%) on the following songs:".format(len(failures), percent_failed))
            for failure in failures:
                print("- {}".format(failure))
        else:
            print("[DONE] STATUS: There were no detected errors")


if __name__ == "__main__":
    main()

