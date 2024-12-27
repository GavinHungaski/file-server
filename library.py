#!/usr/bin/env python

#Author: Gavin Hungaski, Thomas Schappell
#Purpose: Contains a library of functions that can be used both for the client and the server, as well as testing functions for the functions. 

import os
import unittest

testing = False
homeDirectory = ""

def really_recv(client, length):
        data = bytearray()
        while len(data) < length:
                chunk = client.recv(1)
                if not chunk or chunk == b'~':
                        break
                data.extend(chunk)
        return bytes(data)

def is_recursive(content):
        if '-r' in content:
            content.remove('-r')
            return True
        elif '-R' in content:
            content.remove('-R')
            return True
        return False

#"Print colors in Python terminal." GeeksforGeeks. Retrieved from https://www.geeksforgeeks.org/print-colors-python-terminal/. Accessed 3 Dec 2024.

def prCyan(skk): print("\033[96m {}\033[00m" .format(skk))
def prRed(skk): print("\033[91m {}\033[00m" .format(skk))
def prGreen(skk): print("\033[92m {}\033[00m" .format(skk))


def storeHomeDirectory(homeDirec):
        global homeDirectory
        homeDirectory = homeDirec


def makeDirectory(path = ""):
        try:
                if (path != ""):
                        os.mkdir(path, 0o766)
                else:
                        print("Need to provide name of new directory")
                        #need to make this return that rather than printing it itself, for purpose of the client seeing it
        except OSError as e:
                if (not testing): print(e)
                else: raise
                
        except Exception as e:
                if (not testing): print(e)
                else: raise


def changeDirectory(path = ""):
        try:
                if (os.path.isdir(path) or path == ""):
                        if (path != ""):
                                os.chdir(path)
                        else:
                                os.chdir(homeDirectory)
                else:
                        raise OSError(2, "Given file rather than directory")
        except OSError as e:
                if (not testing): print(e)
                else: raise


def printWorkingDirectory():
        return os.getcwd()


def listDirectory(path = ""):
        try:
                if (path == ""):
                        files = os.listdir("./")
                else:
                        files = os.listdir(path)
                return files
        
        except OSError as e:
                if (not testing): print(e)
                else: raise


def printDirectory(items):
        for f in items:
                if (os.path.isdir(f)):
                        prCyan(f)
        for f in items:
                if (os.path.isfile(f)):
                       prGreen(f)


class TestLibrary(unittest.TestCase):
        def testStoreHome(self):
                storeHomeDirectory(os.getcwd())
                self.assertTrue(homeDirectory == os.getcwd())

        def testMkdir(self):
                makeDirectory("./testdirect")
                self.assertTrue(os.path.exists("./testdirect"))
                with self.assertRaises(OSError):
                        makeDirectory("./testdirect")
                with self.assertRaises(Exception):
                       makeDirectory("./fakedirect/newdirect")

                os.rmdir("./testdirect")

        def testCd(self):
                makeDirectory("./testdirect")
                storeHomeDirectory(os.getcwd())
                changeDirectory("./testdirect")
                self.assertTrue(os.getcwd() == (homeDirectory + "/testdirect"))
                changeDirectory()
                self.assertTrue(os.getcwd() == homeDirectory)
                os.rmdir("./testdirect")
                testFilePath = "testfile.txt"
                with open(testFilePath, 'w') as file:
                        file.write("Hello World")
                with self.assertRaises(OSError):
                        changeDirectory(testFilePath)
                os.remove(testFilePath)
                with self.assertRaises(OSError):
                        changeDirectory("./fakedirect")

        def testPWD(self):
                pass
                

if __name__ == '__main__':
        testing = True
        unittest.main()
