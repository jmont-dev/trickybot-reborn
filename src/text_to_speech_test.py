import os
import pyttsx3

# Initialize the text-to-speech engine
engine = pyttsx3.init(driverName='sapi5')

# Set the text to be spoken
text = "Hello, my name is trickybot. I am an artificial intelligence designed to interact with users in this channel"

print(f"Voices are {engine.getProperty('voices')}")

# Set the volume and rate of speech
engine.setProperty('volume', 1.0)
engine.setProperty('rate', 150)
engine.setProperty('voice',"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_enUS_EvaM")

# Save the spoken audio to a file
engine.save_to_file(text, "speech.mp3")

# Play the audio file
#engine.startLoop(False)

#Test all voices
#voices = engine.getProperty('voices')
#for voice in voices:
#   print(f"{voice}")
#   engine.setProperty('voice', voice.id)  # changes the voice
#   engine.say('The quick brown fox jumped over the lazy dog.')

engine.say(text)
#engine.stopLoop()

# Close the text-to-speech engine
engine.runAndWait()