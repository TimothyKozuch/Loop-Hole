import sys


class Composition:
    def __init__(self,name,number):
        self.name = name
        self.compositionNumber = number
        self.clef = None
        self.keySignature = []
        self.notes = []  # Each note: (x, note_index)
        self.timeSignature = []

    def changeClef(self,newClef):
        self.clef = newClef

    def changeKeySig(self,newKeySigIndex,newKeySigSign):
        self.keySignature[newKeySigIndex] = newKeySigSign

    def changeTimeSig(self,newTimeSigIndex,newTimeSigNum):
        self.timeSignature[newTimeSigIndex] = newTimeSigNum

    def changeNote(self,newNoteIndex,newNote):
        self.keySignature[newNoteIndex] = newNote

    def play_song(self):
        print("Playing song (implement sound playback here)")
