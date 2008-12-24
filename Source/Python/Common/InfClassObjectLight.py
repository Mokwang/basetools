## @file
# This file is used to define each component of INF file
#
# Copyright (c) 2007, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.  The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

##
# Import Modules
#
import os
import re
import EdkLogger
from CommonDataClass.CommonClass import LibraryClassClass
from CommonDataClass.ModuleClass import *
from String import *
from DataType import *
from Identification import *
from Dictionary import *
from BuildToolError import *
from Misc import sdict
from Misc import GetFiles
import GlobalData
from Table.TableInf import TableInf
import Database
from Parsing import *

# Global variable
Section = {TAB_UNKNOWN.upper() : MODEL_UNKNOWN,
           TAB_INF_DEFINES.upper() : MODEL_META_DATA_HEADER,
           TAB_BUILD_OPTIONS.upper() : MODEL_META_DATA_BUILD_OPTION,
           TAB_INCLUDES.upper() : MODEL_EFI_INCLUDE,
           TAB_LIBRARIES.upper() : MODEL_EFI_LIBRARY_INSTANCE,
           TAB_LIBRARY_CLASSES.upper() : MODEL_EFI_LIBRARY_CLASS,
           TAB_PACKAGES.upper() : MODEL_META_DATA_PACKAGE,
           TAB_NMAKE.upper() : MODEL_META_DATA_NMAKE,
           TAB_INF_FIXED_PCD.upper() : MODEL_PCD_FIXED_AT_BUILD,
           TAB_INF_PATCH_PCD.upper() : MODEL_PCD_PATCHABLE_IN_MODULE,
           TAB_INF_FEATURE_PCD.upper() : MODEL_PCD_FEATURE_FLAG,
           TAB_INF_PCD_EX.upper() : MODEL_PCD_DYNAMIC_EX,
           TAB_INF_PCD.upper() : MODEL_PCD_DYNAMIC,
           TAB_SOURCES.upper() : MODEL_EFI_SOURCE_FILE,
           TAB_GUIDS.upper() : MODEL_EFI_GUID,
           TAB_PROTOCOLS.upper() : MODEL_EFI_PROTOCOL,
           TAB_PPIS.upper() : MODEL_EFI_PPI,
           TAB_DEPEX.upper() : MODEL_EFI_DEPEX,
           TAB_BINARIES.upper() : MODEL_EFI_BINARY_FILE,
           TAB_USER_EXTENSIONS.upper() : MODEL_META_DATA_USER_EXTENSION
           }

gComponentType2ModuleType = {
    "LIBRARY"               :   "BASE",
    "SECURITY_CORE"         :   "SEC",
    "PEI_CORE"              :   "PEI_CORE",
    "COMBINED_PEIM_DRIVER"  :   "PEIM",
    "PIC_PEIM"              :   "PEIM",
    "RELOCATABLE_PEIM"      :   "PEIM",
    "PE32_PEIM"             :   "PEIM",
    "BS_DRIVER"             :   "DXE_DRIVER",
    "RT_DRIVER"             :   "DXE_RUNTIME_DRIVER",
    "SAL_RT_DRIVER"         :   "DXE_SAL_DRIVER",
    "APPLICATION"           :   "UEFI_APPLICATION",
    "LOGO"                  :   "BASE",
}

gNmakeFlagPattern = re.compile("(?:EBC_)?([A-Z]+)_(?:STD_|PROJ_|ARCH_)?FLAGS(?:_DLL|_ASL|_EXE)?", re.UNICODE)
gNmakeFlagName2ToolCode = {
    "C"         :   "CC",
    "LIB"       :   "SLINK",
    "LINK"      :   "DLINK",
}

class InfHeader(ModuleHeaderClass):
    _Mapping_ = {
        #
        # Required Fields
        #
        TAB_INF_DEFINES_BASE_NAME                   : "Name",
        TAB_INF_DEFINES_FILE_GUID                   : "Guid",
        TAB_INF_DEFINES_MODULE_TYPE                 : "ModuleType",
        TAB_INF_DEFINES_EFI_SPECIFICATION_VERSION   : "EfiSpecificationVersion",
        TAB_INF_DEFINES_EDK_RELEASE_VERSION         : "EdkReleaseVersion",        
        #
        # Optional Fields
        #
        TAB_INF_DEFINES_INF_VERSION                 : "InfVersion",
        TAB_INF_DEFINES_BINARY_MODULE               : "BinaryModule",
        TAB_INF_DEFINES_COMPONENT_TYPE              : "ComponentType",
        TAB_INF_DEFINES_MAKEFILE_NAME               : "MakefileName",
        TAB_INF_DEFINES_BUILD_NUMBER                : "BuildNumber",
        TAB_INF_DEFINES_BUILD_TYPE                  : "BuildType",
        TAB_INF_DEFINES_FFS_EXT                     : "FfsExt",
        TAB_INF_DEFINES_FV_EXT                      : "FvExt",
        TAB_INF_DEFINES_SOURCE_FV                   : "SourceFv",
        TAB_INF_DEFINES_VERSION_NUMBER              : "VersionNumber",
        TAB_INF_DEFINES_VERSION_STRING              : "VersionString",
        TAB_INF_DEFINES_VERSION                     : "Version",
        TAB_INF_DEFINES_PCD_IS_DRIVER               : "PcdIsDriver",
        TAB_INF_DEFINES_TIANO_R8_FLASHMAP_H         : "TianoR8FlashMap_h",
        TAB_INF_DEFINES_SHADOW                      : "Shadow",
#       TAB_INF_DEFINES_LIBRARY_CLASS               : "LibraryClass",
#        TAB_INF_DEFINES_ENTRY_POINT                 : "ExternImages",
#        TAB_INF_DEFINES_UNLOAD_IMAGE                : "ExternImages",
#        TAB_INF_DEFINES_CONSTRUCTOR                 : ,
#        TAB_INF_DEFINES_DESTRUCTOR                  : ,
#        TAB_INF_DEFINES_DEFINE                      : "Define",
#        TAB_INF_DEFINES_SPEC                        : "Specification",
#        TAB_INF_DEFINES_CUSTOM_MAKEFILE             : "CustomMakefile",
#        TAB_INF_DEFINES_MACRO                       : 
    }

    def __init__(self):
        ModuleHeaderClass.__init__(self)
        self.VersionNumber = ''
        self.VersionString = ''
        #print self.__dict__
    def __setitem__(self, key, value):
        self.__dict__[self._Mapping_[key]] = value
    def __getitem__(self, key):
        return self.__dict__[self._Mapping_[key]]
    ## "in" test support
    def __contains__(self, key):
        return key in self._Mapping_

## InfObject
#
# This class defined basic Inf object which is used by inheriting
# 
# @param object:       Inherited from object class
#
class InfObject(object):
    def __init__(self):
        object.__init__()

## Inf
#
# This class defined the structure used in Inf object
# 
# @param InfObject:         Inherited from InfObject class
# @param Ffilename:         Input value for Ffilename of Inf file, default is None
# @param IsMergeAllArches:  Input value for IsMergeAllArches
#                           True is to merge all arches
#                           Fales is not to merge all arches
#                           default is False
# @param IsToModule:        Input value for IsToModule
#                           True is to transfer to ModuleObject automatically
#                           False is not to transfer to ModuleObject automatically
#                           default is False
# @param WorkspaceDir:      Input value for current workspace directory, default is None
#
# @var Identification:      To store value for Identification, it is a structure as Identification
# @var UserExtensions:      To store value for UserExtensions
# @var Module:              To store value for Module, it is a structure as ModuleClass
# @var WorkspaceDir:        To store value for WorkspaceDir
# @var KeyList:             To store value for KeyList, a list for all Keys used in Inf
#
class Inf(InfObject):
    def __init__(self, Filename = None, IsToModule = False, WorkspaceDir = None, PackageDir = None, SupArchList = DataType.ARCH_LIST):
        self.Identification = Identification()
        self.Module = ModuleClass()
        self.UserExtensions = ''
        self.WorkspaceDir = WorkspaceDir
        self.PackageDir = PackageDir
        self.SupArchList = SupArchList
        
        self.KeyList = [
            TAB_SOURCES, TAB_BUILD_OPTIONS, TAB_BINARIES, TAB_INCLUDES, TAB_GUIDS, 
            TAB_PROTOCOLS, TAB_PPIS, TAB_LIBRARY_CLASSES, TAB_PACKAGES, TAB_LIBRARIES, 
            TAB_INF_FIXED_PCD, TAB_INF_PATCH_PCD, TAB_INF_FEATURE_PCD, TAB_INF_PCD, 
            TAB_INF_PCD_EX, TAB_DEPEX, TAB_NMAKE, TAB_INF_DEFINES
        ]
        # Upper all KEYs to ignore case sensitive when parsing
        self.KeyList = map(lambda c: c.upper(), self.KeyList)
        
        # Init RecordSet
        self.RecordSet = {}        
        for Key in self.KeyList:
            self.RecordSet[Section[Key]] = []
        
        # Init Comment
        self.SectionHeaderCommentDict = {}
        
        # Load Inf file if filename is not None
        if Filename != None:
            self.LoadInfFile(Filename)
        
        # Transfer to Module Object if IsToModule is True
        if IsToModule:
            self.InfToModule()

    ## Module Object to INF file
    def ModuleToInf(self, Module):
        Inf = ''
        InfList = sdict()
        SectionHeaderCommentDict = {}
        if Module == None:
            return Inf

        ModuleHeader = Module.ModuleHeader
        TmpList = []
        TmpList.append(TAB_INF_DEFINES_BASE_NAME + ' = ' + ModuleHeader.Name)
        TmpList.append(TAB_INF_DEFINES_FILE_GUID + ' = ' + ModuleHeader.Guid)
        TmpList.append(TAB_INF_DEFINES_VERSION + ' = ' + ModuleHeader.Version)
        TmpList.append(TAB_INF_DEFINES_PCD_IS_DRIVER + ' = ' + ModuleHeader.PcdIsDriver)
        if Module.UserExtensions != None:
            for Item in Module.UserExtensions.Defines:
                TmpList.append(Item)
        InfList['Defines'] = TmpList
        if ModuleHeader.HelpText != '':
            SectionHeaderCommentDict['Defines'] = ModuleHeader.HelpText
        
        if Module.UserExtensions != None:
            InfList['BuildOptions'] = Module.UserExtensions.BuildOptions
        
        for Item in Module.Includes:
            Key = 'Includes.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.FilePath)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.LibraryClasses:
            Key = 'LibraryClasses.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            NewValue = Item.LibraryClass
            if Item.FeatureFlag != '':
                NewValue = NewValue + '|' + Item.FeatureFlag
            Value.append(NewValue)    
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.PackageDependencies:
            Key = 'Packages.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.FilePath)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.PcdCodes:
            Key = 'Pcds' + Item.ItemType + '.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            NewValue = Item.TokenSpaceGuidCName + '.' + Item.CName
            if Item.DefaultValue != '':
                NewValue = NewValue + '|' + Item.DefaultValue
            Value.append(NewValue)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.Sources:
            Key = 'Sources.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            NewValue = Item.SourceFile
            if Item.ToolChainFamily != '':
                NewValue = NewValue + '|' + Item.ToolChainFamily
            if Item.TagName != '':
                NewValue = NewValue + '|' + Item.TagName
            if Item.ToolCode != '':
                NewValue = NewValue + '|' + Item.ToolCode
            if Item.FeatureFlag != '':
                NewValue = NewValue + '|' + Item.FeatureFlag
            Value.append(NewValue)
            if Item.HelpText != '':
                SectionHeaderCommentDict[Key] = Item.HelpText
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.Guids:
            Key = 'Guids.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.CName)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.Protocols:
            Key = 'Protocols.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.CName)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.Ppis:
            Key = 'Ppis.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.CName)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.Ppis:
            Key = 'Ppis.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.CName)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)
        
        for Item in Module.Depex:
            Key = 'Depex.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            Value.append(Item.Depex)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)

        for Item in Module.Binaries:
            Key = 'Binaries.' + Item.SupArchList
            Value = GetHelpTextList(Item.HelpTextList)
            NewValue = Item.FileType + '|' + Item.BinaryFile + '|' + Item.Target
            if Item.FeatureFlag != '':
                NewValue = NewValue + '|' + Item.FeatureFlag
            Value.append(NewValue)
            if Key not in InfList:
                InfList[Key] = [Value]
            else:
                InfList[Key].append(Value)

        # Transfer Module to Inf
        for Key in InfList:
            if Key in SectionHeaderCommentDict:
                List = SectionHeaderCommentDict[Key].split('\r')
                for Item in List:
                    Inf = Inf + Item + '\n'
            Inf = Inf + '[' + Key + ']' + '\n'
            for Value in InfList[Key]:
                if type(Value) == type([]):
                    for SubValue in Value:
                        Inf = Inf + '  ' + SubValue + '\n'
                else:
                    Inf = Inf + '  ' + Value + '\n'
            Inf = Inf + '\n'
        
        return Inf
    
    
    ## Transfer to Module Object
    # 
    # Transfer all contents of an Inf file to a standard Module Object
    #
    def InfToModule(self):
        # Init global information for the file
        ContainerFile = self.Identification.FileFullPath
        
        # Generate Module Header
        self.GenModuleHeader(ContainerFile)
        
        # Generate BuildOptions
        self.GenBuildOptions(ContainerFile)
        
        # Generate Includes
        self.GenIncludes(ContainerFile)
        
        # Generate Libraries
        #self.GenLibraries(ContainerFile)
        
        # Generate LibraryClasses
        self.GenLibraryClasses(ContainerFile)
        
        # Generate Packages
        self.GenPackages(ContainerFile)
        
        # Generate Nmakes
        #self.GenNmakes(ContainerFile)
        
        # Generate Pcds
        self.GenPcds(ContainerFile)
        
        # Generate Sources
        self.GenSources(ContainerFile)
        
        # Generate Guids
        self.GenGuidProtocolPpis(DataType.TAB_GUIDS, ContainerFile)

        # Generate Protocols
        self.GenGuidProtocolPpis(DataType.TAB_PROTOCOLS, ContainerFile)

        # Generate Ppis
        self.GenGuidProtocolPpis(DataType.TAB_PPIS, ContainerFile)
        
        # Generate Depexes
        self.GenDepexes(ContainerFile)
        
        # Generate Binaries
        self.GenBinaries(ContainerFile)
        
        # Init MiscFiles
        self.Module.MiscFiles = MiscFileClass()

    ## Parse [Defines] section
    #
    # Parse [Defines] section into InfDefines object
    #
    # @param InfFile    The path of the INF file
    # @param Section    The title of "Defines" section
    # @param Lines      The content of "Defines" section
    #
    def ParseDefines(self, InfFile, Section, Lines):
        TokenList = Section.split(TAB_SPLIT)
        if len(TokenList) == 3:
            RaiseParserError(Section, "Defines", InfFile, "[xx.yy.%s] format (with platform) is not supported")
        if len(TokenList) == 2:
            Arch = TokenList[1].upper()
        else:
            Arch = TAB_ARCH_COMMON

        if Arch not in self.Defines:
            self.Defines[Arch] = InfDefines()
        GetSingleValueOfKeyFromLines(Lines, self.Defines[Arch].DefinesDictionary, 
                                     TAB_COMMENT_SPLIT, TAB_EQUAL_SPLIT, False, None)

    ## Load Inf file
    #
    # Load the file if it exists
    #
    # @param Filename:  Input value for filename of Inf file
    #
    def LoadInfFile(self, Filename):     
        # Insert a record for file
        Filename = NormPath(Filename)
        self.Identification.FileFullPath = Filename
        (self.Identification.FileRelativePath, self.Identification.FileName) = os.path.split(Filename)
        if self.PackageDir:
            self.Identification.PackagePath = self.PackageDir
        else:
            if self.Identification.FileRelativePath.find(self.WorkspaceDir) > -1:
                self.Identification.PackagePath = self.Identification.FileRelativePath[len(self.WorkspaceDir) + 1:]
            else:
                self.Identification.PackagePath = self.Identification.FileRelativePath
        
        # Init common datas
        IfDefList, SectionItemList, CurrentSection, ArchList, ThirdList, IncludeFiles = \
        [], [], TAB_UNKNOWN, [], [], []
        LineNo = 0
        
        # Parse file content
        IsFindBlockComment = False
        ReservedLine = ''
        Comment = ''
        for Line in open(Filename, 'r'):
            LineNo = LineNo + 1
            # Remove comment block
            if Line.find(TAB_COMMENT_R8_START) > -1:
                ReservedLine = GetSplitValueList(Line, TAB_COMMENT_R8_START, 1)[0]
                IsFindBlockComment = True
            if Line.find(TAB_COMMENT_R8_END) > -1:
                Line = ReservedLine + GetSplitValueList(Line, TAB_COMMENT_R8_END, 1)[1]
                ReservedLine = ''
                IsFindBlockComment = False
            if IsFindBlockComment:
                continue
            
            # Remove comments at tail and remove spaces again
            if Line.strip().startswith(TAB_COMMENT_SPLIT) or Line.strip().startswith('--/'):
                Comment = Comment + Line.strip() + '\n'
            Line = CleanString(Line)
            if Line == '':
                continue
            
            ## Find a new section tab
            # First insert previous section items
            # And then parse the content of the new section
            if Line.startswith(TAB_SECTION_START) and Line.endswith(TAB_SECTION_END):
                if Line[1:3] == "--":
                    continue
                Model = Section[CurrentSection.upper()]
                # Insert items data of previous section
                InsertSectionItems(Model, CurrentSection, SectionItemList, ArchList, ThirdList, self.RecordSet)
                
                # Parse the new section
                SectionItemList = []
                ArchList = []
                ThirdList = []
                
                CurrentSection = ''
                LineList = GetSplitValueList(Line[len(TAB_SECTION_START):len(Line) - len(TAB_SECTION_END)], TAB_COMMA_SPLIT)
                for Item in LineList:
                    ItemList = GetSplitValueList(Item, TAB_SPLIT)
                    if CurrentSection == '':
                        CurrentSection = ItemList[0]
                    else:
                        if CurrentSection != ItemList[0]:
                            EdkLogger.error("Parser", PARSER_ERROR, "Different section names '%s' and '%s' are found in one section definition, this is not allowed." % (CurrentSection, ItemList[0]), File=Filename, Line=LineNo, RaiseError = EdkLogger.IsRaiseError)
                    if CurrentSection.upper() not in self.KeyList:
                        RaiseParserError(Line, CurrentSection, Filename, '', LineNo)
                    ItemList.append('')
                    ItemList.append('')
                    if len(ItemList) > 5:
                        RaiseParserError(Line, CurrentSection, Filename, '', LineNo)
                    else:
                        if ItemList[1] != '' and ItemList[1].upper() not in ARCH_LIST_FULL:
                            EdkLogger.error("Parser", PARSER_ERROR, "Invalid Arch definition '%s' found" % ItemList[1], File=Filename, Line=LineNo, RaiseError = EdkLogger.IsRaiseError)
                        ArchList.append(ItemList[1].upper())
                        ThirdList.append(ItemList[2])

                if Comment:
                    self.SectionHeaderCommentDict[Section[CurrentSection.upper()]] = Comment
                    Comment = ''
                continue
            
            # Not in any defined section
            if CurrentSection == TAB_UNKNOWN:
                ErrorMsg = "%s is not in any defined section" % Line
                EdkLogger.error("Parser", PARSER_ERROR, ErrorMsg, File=Filename, Line=LineNo, RaiseError = EdkLogger.IsRaiseError)

            # Add a section item
            SectionItemList.append([Line, LineNo, Comment])
            Comment = ''
            # End of parse
        #End of For
        
        # Insert items data of last section
        Model = Section[CurrentSection.upper()]
        InsertSectionItems(Model, CurrentSection, SectionItemList, ArchList, ThirdList, self.RecordSet)
        if Comment != '':
            self.SectionHeaderCommentDict[Model] = Comment
            Comment = ''

    
    ## Show detailed information of Module
    #
    # Print all members and their values of Module class
    #
    def ShowModule(self):
        print self.Identification.FileName
        print self.Identification.FileRelativePath
        print self.Identification.PackagePath
        M = self.Module
        print 'Filename =', M.ModuleHeader.FileName
        print 'FullPath =', M.ModuleHeader.FullPath
        print 'BaseName =', M.ModuleHeader.Name
        print 'Guid =', M.ModuleHeader.Guid
        print 'Version =', M.ModuleHeader.Version

        for Item in self.Module.ExternImages:
            print '\nEntry_Point = %s, UnloadImage = %s' % (Item.ModuleEntryPoint, Item.ModuleUnloadImage)
        for Item in self.Module.ExternLibraries:
            print 'Constructor = %s, Destructor = %s' % (Item.Constructor, Item.Destructor)
        print '\nBuildOptions ='
        for Item in M.BuildOptions:
            print Item.ToolChainFamily, Item.ToolChain, Item.Option, Item.SupArchList
        print '\nIncludes ='
        for Item in M.Includes:
            print Item.FilePath, Item.SupArchList
        print '\nLibraries ='
        for Item in M.Libraries:
            print Item.Library, Item.SupArchList
        print '\nLibraryClasses ='
        for Item in M.LibraryClasses:
            print Item.LibraryClass, Item.RecommendedInstance, Item.FeatureFlag, Item.SupModuleList, Item.SupArchList, Item.Define
        print '\nPackageDependencies ='
        for Item in M.PackageDependencies:
            print Item.FilePath, Item.SupArchList, Item.FeatureFlag
        print '\nNmake ='
        for Item in M.Nmake:
            print Item.Name, Item.Value, Item.SupArchList
        print '\nPcds ='
        for Item in M.PcdCodes:
            print '\tCName=',Item.CName, 'TokenSpaceGuidCName=', Item.TokenSpaceGuidCName, 'DefaultValue=', Item.DefaultValue, 'ItemType=', Item.ItemType, Item.SupArchList
        print '\nSources ='
        for Source in M.Sources:
            print Source.SourceFile, 'Fam=', Source.ToolChainFamily, 'Pcd=', Source.FeatureFlag, 'Tag=', Source.TagName, 'ToolCode=', Source.ToolCode, Source.SupArchList
        print '\nUserExtensions ='
        if M.UserExtensions != None:
            print M.UserExtensions.UserID, M.UserExtensions.Identifier,M.UserExtensions.Content, '\nDefines', M.UserExtensions.Defines, '\nBuildOptions', M.UserExtensions.BuildOptions            
        print '\nGuids ='
        for Item in M.Guids:
            print Item.CName, Item.SupArchList, Item.FeatureFlag
        print '\nProtocols ='
        for Item in M.Protocols:
            print Item.CName, Item.SupArchList, Item.FeatureFlag
        print '\nPpis ='
        for Item in M.Ppis:
            print Item.CName, Item.SupArchList, Item.FeatureFlag
        print '\nDepex ='
        for Item in M.Depex:
            print Item.Depex, Item.SupArchList, Item.Define
        print '\nBinaries ='
        for Binary in M.Binaries:
            print 'Type=', Binary.FileType, 'Target=', Binary.Target, 'Name=', Binary.BinaryFile, 'FeatureFlag=', Binary.FeatureFlag, 'SupArchList=', Binary.SupArchList
        for Item in M.FileList:
            print Item

    ## Convert [Defines] section content to ModuleHeaderClass
    #
    # Convert [Defines] section content to ModuleHeaderClass
    #
    # @param Defines        The content under [Defines] section
    # @param ModuleHeader   An object of ModuleHeaderClass
    # @param Arch           The supported ARCH
    #
    def GenModuleHeader(self, ContainerFile):
        EdkLogger.debug(2, "Generate ModuleHeader ...")
        File = self.Identification.FileFullPath
        #
        # Update all defines item in database
        #
        RecordSet = self.RecordSet[MODEL_META_DATA_HEADER]
        
        ModuleHeader = ModuleHeaderClass()
        OtherDefines = []
        for Record in RecordSet:
            ValueList = GetSplitValueList(Record[0], TAB_EQUAL_SPLIT)
            if len(ValueList) != 2:
                OtherDefines.append(Record[0])
            else:
                Name = ValueList[0]
                Value = ValueList[1]
                if Name == TAB_INF_DEFINES_BASE_NAME:
                    ModuleHeader.Name = Value
                elif Name == TAB_INF_DEFINES_FILE_GUID:
                    ModuleHeader.Guid = Value
                elif Name == TAB_INF_DEFINES_VERSION:
                    ModuleHeader.Version = Value
                elif Name == TAB_INF_DEFINES_PCD_IS_DRIVER:
                    ModuleHeader.PcdIsDriver = Value
                else:
                    OtherDefines.append(Record[0])
        ModuleHeader.FileName = self.Identification.FileName
        ModuleHeader.FullPath = self.Identification.FileFullPath
        if MODEL_META_DATA_HEADER in self.SectionHeaderCommentDict:
            ModuleHeader.HelpText = self.SectionHeaderCommentDict[MODEL_META_DATA_HEADER]
        self.Module.ModuleHeader = ModuleHeader
        UE = self.Module.UserExtensions
        if UE == None:
            UE = UserExtensionsClass()
        UE.Defines = OtherDefines
        self.Module.UserExtensions = UE
    
    ## GenBuildOptions
    #
    # Gen BuildOptions of Inf
    # [<Family>:]<ToolFlag>=Flag
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenBuildOptions(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_BUILD_OPTIONS)
        BuildOptions = {}
        #
        # Get all BuildOptions
        #
        RecordSet = self.RecordSet[MODEL_META_DATA_BUILD_OPTION]
        UE = self.Module.UserExtensions
        if UE == None:
            UE = UserExtensionsClass()
        for Record in RecordSet:
            UE.BuildOptions.append(Record[0])
        self.Module.UserExtensions = UE
        
    ## GenIncludes
    #
    # Gen Includes of Inf
    # 
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenIncludes(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_INCLUDES)
        Includes = sdict()
        #
        # Get all Includes
        #
        RecordSet = self.RecordSet[MODEL_EFI_INCLUDE]
        for Record in RecordSet:
            Include = IncludeClass()
            Include.FilePath = Record[0]
            Include.SupArchList = Record[1]
            if GenerateHelpText(Record[5], ''):
                Include.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.Includes.append(Include)
            #self.Module.FileList.extend(GetFiles(os.path.normpath(os.path.join(self.Identification.FileRelativePath, Include.FilePath)), ['CVS', '.svn']))
        
        
    ## GenLibraries
    #
    # Gen Libraries of Inf
    # 
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenLibraries(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_LIBRARIES)
        Libraries = sdict()
        #
        # Get all Includes
        #
        RecordSet = self.RecordSet[MODEL_EFI_LIBRARY_INSTANCE]
        for Record in RecordSet:
            Library = ModuleLibraryClass()
            # replace macro and remove file extension
            Library.Library = Record[0].rsplit('.', 1)[0]
            Library.SupArchList = Record[1]
            if GenerateHelpText(Record[5], ''):
                Library.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.Libraries.append(Library)
    
    ## GenLibraryClasses
    #
    # Get LibraryClass of Inf
    # <LibraryClassKeyWord>|<LibraryInstance>
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenLibraryClasses(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_LIBRARY_CLASSES)
        LibraryClasses = {}
        #
        # Get all LibraryClasses
        #
        RecordSet = self.RecordSet[MODEL_EFI_LIBRARY_CLASS]
        for Record in RecordSet:
            (LibClassName, LibClassIns, Pcd, SupModelList) = GetLibraryClassOfInf([Record[0], Record[4]], ContainerFile, self.WorkspaceDir, Record[2])            
            LibraryClass = LibraryClassClass()
            LibraryClass.LibraryClass = LibClassName
            LibraryClass.RecommendedInstance = LibClassIns
            LibraryClass.FeatureFlag = Pcd
            LibraryClass.SupArchList = Record[1]
            LibraryClass.SupModuleList = GetSplitValueList(SupModelList)
            if GenerateHelpText(Record[5], ''):
                LibraryClass.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.LibraryClasses.append(LibraryClass)

    ## GenPackages
    #
    # Gen Packages of Inf
    # 
    # @param ContainerFile: The Inf file full path 
    #
    def GenPackages(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_PACKAGES)
        Packages = {}
        # Get all Packages
        RecordSet = self.RecordSet[MODEL_META_DATA_PACKAGE]
        for Record in RecordSet:
            (PackagePath, Pcd) = GetPackage(Record[0], ContainerFile, self.WorkspaceDir, Record[2])
            Package = ModulePackageDependencyClass()
            Package.FilePath = NormPath(PackagePath)
            Package.SupArchList = Record[1]
            Package.FeatureFlag = Pcd
            if GenerateHelpText(Record[5], ''):
                Package.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.PackageDependencies.append(Package)

    ## GenNmakes
    #
    # Gen Nmakes of Inf
    # 
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenNmakes(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_NMAKE)
        Nmakes = sdict()
        # Get all Nmakes
        RecordSet = self.RecordSet[MODEL_META_DATA_NMAKE]

        # Go through each arch
        for Arch in self.SupArchList:
            for Record in RecordSet:
                if Record[1] == Arch or Record[1] == TAB_ARCH_COMMON:
                    MergeArches(Nmakes, Record[0], Arch)
                
        for Key in Nmakes.keys():
            List = GetSplitValueList(Key, DataType.TAB_EQUAL_SPLIT, MaxSplit=1)
            if len(List) != 2:
                RaiseParserError(Key, 'Nmake', ContainerFile, '<MacroName> = <Value>')
            Nmake = ModuleNmakeClass()
            Nmake.Name = List[0]
            Nmake.Value = List[1]
            Nmake.SupArchList = Nmakes[Key]
            if GenerateHelpText(Record[5], ''):
                Nmake.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.Nmake.append(Nmake)
    
    def AddPcd(self, CName, TokenSpaceGuidCName, DefaultValue, ItemType, Arch, HelpTextList):
        Pcd = PcdClass()
        Pcd.CName = CName
        Pcd.TokenSpaceGuidCName = TokenSpaceGuidCName
        Pcd.DefaultValue = DefaultValue
        Pcd.ItemType = ItemType
        Pcd.SupArchList = Arch
        if GenerateHelpText(HelpTextList, ''):
            Pcd.HelpTextList.append(GenerateHelpText(HelpTextList, ''))
        self.Module.PcdCodes.append(Pcd)
    
    ## GenPcds
    #
    # Gen Pcds of Inf
    # <TokenSpaceGuidCName>.<PcdCName>[|<Value>]
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenPcds(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_PCDS)
        Pcds = {}
        PcdToken = {}
        
        # Get all Pcds
        RecordSet1 = self.RecordSet[MODEL_PCD_FIXED_AT_BUILD]
        RecordSet2 = self.RecordSet[MODEL_PCD_PATCHABLE_IN_MODULE]
        RecordSet3 = self.RecordSet[MODEL_PCD_FEATURE_FLAG]
        RecordSet4 = self.RecordSet[MODEL_PCD_DYNAMIC_EX]
        RecordSet5 = self.RecordSet[MODEL_PCD_DYNAMIC]
        
        # Go through each arch
        for Record in RecordSet1:
            (TokenSpaceGuidCName, TokenName, Value, Type) = GetPcdOfInf(Record[0], TAB_PCDS_FIXED_AT_BUILD, ContainerFile, Record[2])
            self.AddPcd(TokenName, TokenSpaceGuidCName, Value, Type, Record[1], Record[5])
        for Record in RecordSet2:
            (TokenSpaceGuidCName, TokenName, Value, Type) = GetPcdOfInf(Record[0], TAB_PCDS_PATCHABLE_IN_MODULE, ContainerFile, Record[2])
            self.AddPcd(TokenName, TokenSpaceGuidCName, Value, Type, Record[1], Record[5])
        for Record in RecordSet3:
            (TokenSpaceGuidCName, TokenName, Value, Type) = GetPcdOfInf(Record[0], TAB_PCDS_FEATURE_FLAG, ContainerFile, Record[2])
            self.AddPcd(TokenName, TokenSpaceGuidCName, Value, Type, Record[1], Record[5])
        for Record in RecordSet4:
            (TokenSpaceGuidCName, TokenName, Value, Type) = GetPcdOfInf(Record[0], TAB_PCDS_DYNAMIC_EX, ContainerFile, Record[2])
            self.AddPcd(TokenName, TokenSpaceGuidCName, Value, Type, Record[1], Record[5])
        for Record in RecordSet5:
            (TokenSpaceGuidCName, TokenName, Value, Type) = GetPcdOfInf(Record[0], '', ContainerFile, Record[2])
            self.AddPcd(TokenName, TokenSpaceGuidCName, Value, Type, Record[1], Record[5])
        
    ## GenSources
    #
    # Gen Sources of Inf
    # <Filename>[|<Family>[|<TagName>[|<ToolCode>[|<PcdFeatureFlag>]]]]
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenSources(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_SOURCES)
        Sources = {}
        
        # Get all Nmakes
        RecordSet = self.RecordSet[MODEL_EFI_SOURCE_FILE]
        for Record in RecordSet:
            (Filename, Family, TagName, ToolCode, Pcd) = GetSource(Record[0], ContainerFile, self.Identification.FileRelativePath, Record[2])
            Source = ModuleSourceFileClass(Filename, TagName, ToolCode, Family, Pcd, Record[1])
            if GenerateHelpText(Record[5], ''):
                Source.HelpTextList.append(GenerateHelpText(Record[5], ''))
            if MODEL_EFI_SOURCE_FILE in self.SectionHeaderCommentDict:
                Source.HelpText = self.SectionHeaderCommentDict[MODEL_EFI_SOURCE_FILE]
            self.Module.Sources.append(Source)
            self.Module.FileList.append(os.path.normpath(os.path.join(self.Identification.FileRelativePath, Filename)))
    
    ## GenUserExtensions
    #
    # Gen UserExtensions of Inf
    #
    def GenUserExtensions(self, ContainerFile):
        pass

    ## GenDepexes
    #
    # Gen Depex of Inf
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenDepexes(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_DEPEX)
        Depex = {}
        # Get all Depexes
        RecordSet = self.RecordSet[MODEL_EFI_DEPEX]
        for Record in RecordSet:
            Dep = ModuleDepexClass()
            Dep.Depex = Record[0]
            Dep.SupArchList = Record[1]
            if GenerateHelpText(Record[5], ''):
                Dep.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.Depex.append(Dep)

    ## GenBinaries
    #
    # Gen Binary of Inf
    # <FileType>|<Filename>|<Target>[|<TokenSpaceGuidCName>.<PcdCName>]
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenBinaries(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_BINARIES)
        Binaries = {}
        
        # Get all Guids
        RecordSet = self.RecordSet[MODEL_EFI_BINARY_FILE]
        for Record in RecordSet:
            (FileType, Filename, Target, Pcd) = GetBinary(Record[0], ContainerFile, self.Identification.FileRelativePath, Record[2])
            Binary = ModuleBinaryFileClass(Filename, FileType, Target, Pcd, Record[1])
            if GenerateHelpText(Record[5], ''):
                Binary.HelpTextList.append(GenerateHelpText(Record[5], ''))
            self.Module.Binaries.append(Binary)
            self.Module.FileList.append(os.path.normpath(os.path.join(self.Identification.FileRelativePath, Filename)))
        
    ## GenGuids
    #
    # Gen Guids of Inf
    # <CName>=<GuidValue>
    #
    # @param ContainerFile: The Inf file full path 
    #
    def GenGuidProtocolPpis(self, Type, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % Type)
        Lists = {}
        # Get all Items
        if Type == TAB_GUIDS:
            ListMember = self.Module.Guids
        elif Type == TAB_PROTOCOLS:
            ListMember = self.Module.Protocols
        elif Type == TAB_PPIS:
            ListMember = self.Module.Ppis

        RecordSet = self.RecordSet[Section[Type.upper()]]
        for Record in RecordSet:
            (Name, Value) = GetGuidsProtocolsPpisOfInf(Record[0], Type, ContainerFile, Record[2])
            ListClass = GuidProtocolPpiCommonClass()
            ListClass.CName = Name
            ListClass.SupArchList = Record[1]
            ListClass.FeatureFlag = Value
            if GenerateHelpText(Record[5], ''):
                ListClass.HelpTextList.append(GenerateHelpText(Record[5], ''))
            ListMember.append(ListClass)
       
##
#
# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
#
if __name__ == '__main__':
    EdkLogger.Initialize()
    EdkLogger.SetLevel(EdkLogger.QUIET)
        
    W = os.getenv('WORKSPACE')
    F = os.path.join(W, 'MdeModulePkg/Application/HelloWorld/HelloWorld.inf')
    
    P = Inf(os.path.normpath(F), True, W)
    P.ShowModule()
    print P.ModuleToInf(P.Module)
