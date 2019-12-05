import json

from fontTools import ttLib
from random import shuffle
from kerndump import getKerningPairsFromOTF

# ==================================================

# User-editable variables

# This won't take effect until the cache is recalculated
CASE = "IC" # "UC" / "LC" / "IC" (Initial Cap)

# Shuffle the word list (false = alphabetical order)
# This won't take effect until the cache is recalculated
SHUFFLE = True

# Recompute word length values
# (necessary if changing CASE, SHUFFLE, font or wordlist)
CLEAR_CACHE = False

# Limit the number of words to compute from the wordlist
# Take off some zeroes if things are getting slow
CACHE_WORD_LIMIT = 100000

FILE_FONT = "Greymarch-Regular.otf"
FILE_WORDLIST = "lc58k.txt"
FILE_CACHE = "cache.json" # MAY BE OVERWRITTEN!

# Length (in font units) the words should be
TARGET_LENGTH = 400 * 10
MISS_TOLERANCE = 10

# Disabling this will enable ttf support at a cost of accuracy
CONSIDER_KERNS = True

WORD_COUNT = 10

# If the word count is not met, increase miss tolerance and retry
INCREASE_TOLERANCE_ON_FAIL = True

# Amount to multiply miss tolerance by each time
MISS_TOLERANCE_MULTIPLIER = 1.25

# How many times to try before giving up
TARGET_MISS_RECYCLE_COUNT = 10

# ==================================================

word_list = []
compute_lengths = {}
compute_from_file = False
output = []

# Attempt to load pre-computed word lengths from file
try:
    with open(FILE_CACHE, 'r') as f:
        compute_lengths = json.load(f)
    compute_from_file = True
except:
    print("Cached word lengths could not be loaded from file and will be recalculated.")

# tbh this function should return the computed word lengths
# but it just sets the variable elsewhere  ¯\_(ツ)_/¯
def compute_word_lengths():
    with open(FILE_WORDLIST, 'r') as f:
        for line in f:
            if CASE is "UC":
                word_list.append(line.strip().upper())
            elif CASE is "IC":
                word_list.append(line.strip().capitalize())
            else:
                word_list.append(line.strip().lower())

    f = ttLib.TTFont(FILE_FONT)
    
    # Unicode character map
    cmap = f['cmap'].getcmap(3,1).cmap
    gset = f.getGlyphSet()
    
    # getKerningPairsFromOTF from adobe-type-tools/kern-dump
    otfKern = getKerningPairsFromOTF.OTFKernReader(FILE_FONT)
    kern = otfKern.kerningPairs

    if SHUFFLE:
        shuffle(word_list)
    
    for word in word_list[:CACHE_WORD_LIMIT]:
        word_length = 0
        for idx, char in enumerate(word):
            if char in gset:
                # If the current character is in the font,
                # add its advance width to the current word's length
                if ord(char) in cmap and cmap[ord(char)] in gset:
                    word_length += gset[cmap[ord(char)]].width
                    
                    if CONSIDER_KERNS:
                        # If this isn't the last character in the word
                        if idx + 1 < len(word):
                            # And if there's a kerning pair of this character and the next
                            if (char, word[idx + 1]) in kern:
                                # Apply its value to the word length
                                word_length += kern[(char, word[idx + 1])]
                                
        # Finally, add the computed word length to the dict
        compute_lengths[word] = word_length
        
# Recompute word lengths if they couldn't be loaded or manual flag set
if CLEAR_CACHE or not compute_from_file:
    # Reset computed lengths & recalculate
    compute_lengths = {}
    compute_word_lengths()
    with open(FILE_CACHE, 'w') as f:
        f.write(json.dumps(compute_lengths))

# Keep the variables at the top static & create new ones here
m_miss_tolerance = MISS_TOLERANCE
bounds_min = TARGET_LENGTH - m_miss_tolerance
bounds_max = TARGET_LENGTH + m_miss_tolerance
count_so_far = 0
total_cycles = 0
max_cycles = TARGET_MISS_RECYCLE_COUNT if INCREASE_TOLERANCE_ON_FAIL else 1
for cycle in range(max_cycles):
    total_cycles = cycle
    
    # Check each word's length; if it's within tolerance, add it to output
    for word in compute_lengths:
        if count_so_far < WORD_COUNT:
            if bounds_min < compute_lengths[word] < bounds_max:
                if word not in output:
                    count_so_far += 1
                    output.append(word)
    if count_so_far < WORD_COUNT:
        # Update tolerances if we're still below the word count at the end of a cycle
        m_miss_tolerance *= MISS_TOLERANCE_MULTIPLIER
        bounds_min = TARGET_LENGTH - m_miss_tolerance
        bounds_max = TARGET_LENGTH + m_miss_tolerance
    else:
        # Stop looping if we have enough words
        break

if total_cycles > 0:
    # Notify the user that tolerances have been changed
    # Accuracy might be lower than anticipated
    print('Cycled ' + str(total_cycles + 1) + ' times. Eventual miss tolerance: ' + str(m_miss_tolerance))

try:
    # If this is running in drawbot, show the words nicely in the font
    newPage(1000, 750)
    font(FILE_FONT, 50)
    text('\n'.join(output), (75, height() - 100))
except NameError:
    # If drawbot isn't working, act like a cli script
    pass

print('\n'.join(output))