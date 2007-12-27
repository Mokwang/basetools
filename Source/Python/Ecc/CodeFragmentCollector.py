## @file
# preprocess source file
#
#  Copyright (c) 2007, Intel Corporation
#
#  All rights reserved. This program and the accompanying materials
#  are licensed and made available under the terms and conditions of the BSD License
#  which accompanies this distribution.  The full text of the license may be found at
#  http://opensource.org/licenses/bsd-license.php
#
#  THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
#  WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

##
# Import Modules
#

import re
import os
import sys
import FileProfile
from CodeFragment import Comment
from CodeFragment import PP_Directive
from ParserWarning import Warning


##define T_CHAR_SPACE                ' '
##define T_CHAR_NULL                 '\0'
##define T_CHAR_CR                   '\r'
##define T_CHAR_TAB                  '\t'
##define T_CHAR_LF                   '\n'
##define T_CHAR_SLASH                '/'
##define T_CHAR_BACKSLASH            '\\'
##define T_CHAR_DOUBLE_QUOTE         '\"'
##define T_CHAR_SINGLE_QUOTE         '\''
##define T_CHAR_STAR                 '*'
##define T_CHAR_HASH                 '#'

(T_CHAR_SPACE, T_CHAR_NULL, T_CHAR_CR, T_CHAR_TAB, T_CHAR_LF, T_CHAR_SLASH, \
T_CHAR_BACKSLASH, T_CHAR_DOUBLE_QUOTE, T_CHAR_SINGLE_QUOTE, T_CHAR_STAR, T_CHAR_HASH) = \
(' ', '\0', '\r', '\t', '\n', '/', '\\', '\"', '\'', '*', '#')

SEPERATOR_TUPLE = ('=', '|', ',', '{', '}') 

(T_COMMENT_TWO_SLASH, T_COMMENT_SLASH_STAR) = (0, 1)

(T_PP_INCLUDE, T_PP_DEFINE, T_PP_OTHERS) = (0, 1, 2)

## The collector for source code fragments.
#
# PreprocessFile method should be called prior to ParseFile
#
# GetNext*** procedures mean these procedures will get next token first, then make judgement.
# Get*** procedures mean these procedures will make judgement on current token only.
#        
class CodeFragmentCollector:
    ## The constructor
    #
    #   @param  self        The object pointer
    #   @param  FileName    The file that to be parsed
    #
    def __init__(self, FileName):
        self.Profile = FileProfile.FileProfile(FileName)
        self.Profile.FileLinesList.append(list(T_CHAR_LF))
        self.FileName = FileName
        self.CurrentLineNumber = 1
        self.CurrentOffsetWithinLine = 0

        self.__Token = ""
        self.__SkippedChars = ""

    ## __IsWhiteSpace() method
    #
    #   Whether char at current FileBufferPos is whitespace
    #
    #   @param  self        The object pointer
    #   @param  Char        The char to test
    #   @retval True        The char is a kind of white space
    #   @retval False       The char is NOT a kind of white space
    #
    def __IsWhiteSpace(self, Char):
        if Char in (T_CHAR_NULL, T_CHAR_CR, T_CHAR_SPACE, T_CHAR_TAB, T_CHAR_LF):
            return True
        else:
            return False

    ## __SkipWhiteSpace() method
    #
    #   Skip white spaces from current char, return number of chars skipped
    #
    #   @param  self        The object pointer
    #   @retval Count       The number of chars skipped
    #
    def __SkipWhiteSpace(self):
        Count = 0
        while not self.__EndOfFile():
            Count += 1
            if self.__CurrentChar() in (T_CHAR_NULL, T_CHAR_CR, T_CHAR_LF, T_CHAR_SPACE, T_CHAR_TAB):
                self.__SkippedChars += str(self.__CurrentChar())
                self.__GetOneChar()

            else:
                Count = Count - 1
                return Count

    ## __EndOfFile() method
    #
    #   Judge current buffer pos is at file end
    #
    #   @param  self        The object pointer
    #   @retval True        Current File buffer position is at file end
    #   @retval False       Current File buffer position is NOT at file end
    #
    def __EndOfFile(self):
        NumberOfLines = len(self.Profile.FileLinesList)
        SizeOfLastLine = len(self.Profile.FileLinesList[-1])
        if self.CurrentLineNumber == NumberOfLines and self.CurrentOffsetWithinLine >= SizeOfLastLine - 1:
            return True
        else:
            return False

    ## __EndOfLine() method
    #
    #   Judge current buffer pos is at line end
    #
    #   @param  self        The object pointer
    #   @retval True        Current File buffer position is at line end
    #   @retval False       Current File buffer position is NOT at line end
    #
    def __EndOfLine(self):
        SizeOfCurrentLine = len(self.Profile.FileLinesList[self.CurrentLineNumber - 1])
        if self.CurrentOffsetWithinLine >= SizeOfCurrentLine - 1:
            return True
        else:
            return False
    
    ## Rewind() method
    #
    #   Reset file data buffer to the initial state
    #
    #   @param  self        The object pointer
    #
    def Rewind(self):
        self.CurrentLineNumber = 1
        self.CurrentOffsetWithinLine = 0
    
    ## __UndoOneChar() method
    #
    #   Go back one char in the file buffer
    #
    #   @param  self        The object pointer
    #   @retval True        Successfully go back one char
    #   @retval False       Not able to go back one char as file beginning reached
    #    
    def __UndoOneChar(self):
        
        if self.CurrentLineNumber == 1 and self.CurrentOffsetWithinLine == 0:
            return False
        elif self.CurrentOffsetWithinLine == 0:
            self.CurrentLineNumber -= 1
            self.CurrentOffsetWithinLine = len(self.__CurrentLine()) - 1
        else:
            self.CurrentOffsetWithinLine -= 1
        return True
        
    ## __GetOneChar() method
    #
    #   Move forward one char in the file buffer
    #
    #   @param  self        The object pointer
    #  
    def __GetOneChar(self):
        if self.CurrentOffsetWithinLine == len(self.Profile.FileLinesList[self.CurrentLineNumber - 1]) - 1:
                self.CurrentLineNumber += 1
                self.CurrentOffsetWithinLine = 0
        else:
                self.CurrentOffsetWithinLine += 1

    ## __CurrentChar() method
    #
    #   Get the char pointed to by the file buffer pointer
    #
    #   @param  self        The object pointer
    #   @retval Char        Current char
    #  
    def __CurrentChar(self):
        CurrentChar = self.Profile.FileLinesList[self.CurrentLineNumber - 1][self.CurrentOffsetWithinLine]
#        if CurrentChar > 255:
#            raise Warning("Non-Ascii char found At Line %d, offset %d" % (self.CurrentLineNumber, self.CurrentOffsetWithinLine), self.FileName, self.CurrentLineNumber)
        return CurrentChar
    
    ## __NextChar() method
    #
    #   Get the one char pass the char pointed to by the file buffer pointer
    #
    #   @param  self        The object pointer
    #   @retval Char        Next char
    #
    def __NextChar(self):
        if self.CurrentOffsetWithinLine == len(self.Profile.FileLinesList[self.CurrentLineNumber - 1]) - 1:
            return self.Profile.FileLinesList[self.CurrentLineNumber][0]
        else:
            return self.Profile.FileLinesList[self.CurrentLineNumber - 1][self.CurrentOffsetWithinLine + 1]
        
    ## __SetCurrentCharValue() method
    #
    #   Modify the value of current char
    #
    #   @param  self        The object pointer
    #   @param  Value       The new value of current char
    #
    def __SetCurrentCharValue(self, Value):
        self.Profile.FileLinesList[self.CurrentLineNumber - 1][self.CurrentOffsetWithinLine] = Value
        
    ## __CurrentLine() method
    #
    #   Get the list that contains current line contents
    #
    #   @param  self        The object pointer
    #   @retval List        current line contents
    #
    def __CurrentLine(self):
        return self.Profile.FileLinesList[self.CurrentLineNumber - 1]
        
    ## PreprocessFile() method
    #
    #   Preprocess file contents, replace comments with spaces.
    #   In the end, rewind the file buffer pointer to the beginning
    #   BUGBUG: No !include statement processing contained in this procedure
    #   !include statement should be expanded at the same FileLinesList[CurrentLineNumber - 1]
    #
    #   @param  self        The object pointer
    #   
    def PreprocessFile(self):
        
        self.Rewind()
        InComment = False
        DoubleSlashComment = False
        HashComment = False
        PPExtend = False
        CommentObj = None
        PPDirectiveObj = None 

        while not self.__EndOfFile():
            
            # meet new line, then no longer in a comment for // and '#'
            if self.__CurrentChar() == T_CHAR_LF:
                if HashComment and PPDirectiveObj != None:
                    if PPDirectiveObj.Content.rstrip(T_CHAR_CR).endswith(T_CHAR_BACKSLASH):
                        PPDirectiveObj.Content += T_CHAR_LF
                        PPExtend = True
                    else:
                        PPExtend = False
                        
                EndLinePos = (self.CurrentLineNumber, self.CurrentOffsetWithinLine)
                self.CurrentLineNumber += 1
                self.CurrentOffsetWithinLine = 0
                if InComment and DoubleSlashComment:
                    InComment = False
                    DoubleSlashComment = False
                    CommentObj.Content += T_CHAR_LF
                    CommentObj.EndPos = EndLinePos
                    FileProfile.CommentList.append(CommentObj)
                    CommentObj = None
                if InComment and HashComment and not PPExtend:
                    InComment = False
                    HashComment = False
                    PPDirectiveObj.Content += T_CHAR_LF
                    PPDirectiveObj.EndPos = EndLinePos
                    FileProfile.PPDirectiveList.append(PPDirectiveObj)
                    PPDirectiveObj = None
                    
            # check for */ comment end
            elif InComment and not DoubleSlashComment and not HashComment and self.__CurrentChar() == T_CHAR_STAR and self.__NextChar() == T_CHAR_SLASH:
                CommentObj.Content += self.__CurrentChar()
                self.__SetCurrentCharValue(T_CHAR_SPACE)
                self.__GetOneChar()
                CommentObj.Content += self.__CurrentChar()
                self.__SetCurrentCharValue(T_CHAR_SPACE)
                CommentObj.EndPos = (self.CurrentLineNumber, self.CurrentOffsetWithinLine)
                FileProfile.CommentList.append(CommentObj)
                CommentObj = None
                self.__GetOneChar()
                InComment = False
            # set comments to spaces
            elif InComment:                   
                if HashComment:
                    # // follows hash PP directive
                    if self.__CurrentChar() == T_CHAR_SLASH and self.__NextChar() == T_CHAR_SLASH:
                        InComment = False
                        HashComment = False
                        PPDirectiveObj.EndPos = (self.CurrentLineNumber, self.CurrentOffsetWithinLine - 1)
                        FileProfile.PPDirectiveList.append(PPDirectiveObj)
                        PPDirectiveObj = None
                        continue
                    else:
                        PPDirectiveObj.Content += self.__CurrentChar()
                else:
                    CommentObj.Content += self.__CurrentChar()
                self.__SetCurrentCharValue(T_CHAR_SPACE)
                self.__GetOneChar()
            # check for // comment
            elif self.__CurrentChar() == T_CHAR_SLASH and self.__NextChar() == T_CHAR_SLASH:
                InComment = True
                DoubleSlashComment = True
                CommentObj = Comment('', (self.CurrentLineNumber, self.CurrentOffsetWithinLine), None, T_COMMENT_TWO_SLASH)
            # check for '#' comment
            elif self.__CurrentChar() == T_CHAR_HASH:
                InComment = True
                HashComment = True
                PPDirectiveObj = PP_Directive('', (self.CurrentLineNumber, self.CurrentOffsetWithinLine), None)
            # check for /* comment start
            elif self.__CurrentChar() == T_CHAR_SLASH and self.__NextChar() == T_CHAR_STAR:
                CommentObj = Comment('', (self.CurrentLineNumber, self.CurrentOffsetWithinLine), None, T_COMMENT_SLASH_STAR)
                CommentObj.Content += self.__CurrentChar()
                self.__SetCurrentCharValue( T_CHAR_SPACE)
                self.__GetOneChar()
                CommentObj.Content += self.__CurrentChar()
                self.__SetCurrentCharValue( T_CHAR_SPACE)
                self.__GetOneChar()
                InComment = True
            else:
                self.__GetOneChar()

        # restore from ListOfList to ListOfString
        self.Profile.FileLinesList = ["".join(list) for list in self.Profile.FileLinesList]
        self.Rewind()

        
if __name__ == "__main__":
    
    collector = CodeFragmentCollector(sys.argv[1])
    collector.PreprocessFile()
    print "For Test."