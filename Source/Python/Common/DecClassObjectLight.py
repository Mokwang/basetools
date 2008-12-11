## @file
# This file is used to define each component of DEC file in light mode
#
# Copyright (c) 2008, Intel Corporation
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
from String import *
from DataType import *
from Identification import *
from Dictionary import *
from CommonDataClass.PackageClass import *
from CommonDataClass.CommonClass import PcdClass
from BuildToolError import *
from Table.TableDec import TableDec
import Database
from Parsing import *
import GlobalData

#
# Global variable
#
Section = {TAB_UNKNOWN.upper() : MODEL_UNKNOWN,
           TAB_DEC_DEFINES.upper() : MODEL_META_DATA_HEADER,
           TAB_INCLUDES.upper() : MODEL_EFI_INCLUDE,
           TAB_LIBRARY_CLASSES.upper() : MODEL_EFI_LIBRARY_CLASS,
           TAB_COMPONENTS.upper() : MODEL_META_DATA_COMPONENT,
           TAB_GUIDS.upper() : MODEL_EFI_GUID,
           TAB_PROTOCOLS.upper() : MODEL_EFI_PROTOCOL,
           TAB_PPIS.upper() : MODEL_EFI_PPI,
           TAB_PCDS_FIXED_AT_BUILD_NULL.upper() : MODEL_PCD_FIXED_AT_BUILD,
           TAB_PCDS_PATCHABLE_IN_MODULE_NULL.upper() : MODEL_PCD_PATCHABLE_IN_MODULE,
           TAB_PCDS_FEATURE_FLAG_NULL.upper() : MODEL_PCD_FEATURE_FLAG,
           TAB_PCDS_DYNAMIC_EX_NULL.upper() : MODEL_PCD_DYNAMIC_EX,
           TAB_PCDS_DYNAMIC_NULL.upper() : MODEL_PCD_DYNAMIC,
           TAB_USER_EXTENSIONS.upper() : MODEL_META_DATA_USER_EXTENSION
           }


## DecObject
#
# This class defined basic Dec object which is used by inheriting
# 
# @param object:       Inherited from object class
#
class DecObject(object):
    def __init__(self):
        object.__init__()

## Dec
#
# This class defined the structure used in Dec object
# 
# @param DecObject:         Inherited from DecObject class
# @param Filename:          Input value for Filename of Dec file, default is None
# @param IsMergeAllArches:  Input value for IsMergeAllArches
#                           True is to merge all arches
#                           Fales is not to merge all arches
#                           default is False
# @param IsToPackage:       Input value for IsToPackage
#                           True is to transfer to PackageObject automatically
#                           False is not to transfer to PackageObject automatically
#                           default is False
# @param WorkspaceDir:      Input value for current workspace directory, default is None
#
# @var Identification:      To store value for Identification, it is a structure as Identification
# @var Defines:             To store value for Defines, it is a structure as DecDefines
# @var UserExtensions:      To store value for UserExtensions
# @var Package:             To store value for Package, it is a structure as PackageClass
# @var WorkspaceDir:        To store value for WorkspaceDir
# @var Contents:            To store value for Contents, it is a structure as DecContents
# @var KeyList:             To store value for KeyList, a list for all Keys used in Dec
#
class Dec(DecObject):
    def __init__(self, Filename = None, IsToPackage = False, WorkspaceDir = None, SupArchList = DataType.ARCH_LIST):
        self.Identification = Identification()
        self.Package = PackageClass()
        self.UserExtensions = ''
        self.WorkspaceDir = WorkspaceDir
        self.SupArchList = SupArchList

        self.KeyList = [
            TAB_INCLUDES, TAB_GUIDS, TAB_PROTOCOLS, TAB_PPIS, TAB_LIBRARY_CLASSES, \
            TAB_PCDS_FIXED_AT_BUILD_NULL, TAB_PCDS_PATCHABLE_IN_MODULE_NULL, TAB_PCDS_FEATURE_FLAG_NULL, \
            TAB_PCDS_DYNAMIC_NULL, TAB_PCDS_DYNAMIC_EX_NULL, TAB_DEC_DEFINES
        ]
        #
        # Upper all KEYs to ignore case sensitive when parsing
        #
        self.KeyList = map(lambda c: c.upper(), self.KeyList)
        
        #
        # Init RecordSet
        #
        self.RecordSet = {}        
        for Key in self.KeyList:
            self.RecordSet[Section[Key]] = []
        
        #
        # Load Dec file if filename is not None
        #
        if Filename != None:
            self.LoadDecFile(Filename)
        
        #
        # Transfer to Package Object if IsToPackage is True
        #
        if IsToPackage:
            self.DecToPackage()
    
    ## Load Dec file
    #
    # Load the file if it exists
    #
    # @param Filename:  Input value for filename of Dec file
    #
    def LoadDecFile(self, Filename):
        #
        # Insert a record for file
        #
        Filename = NormPath(Filename)
        self.Identification.FileFullPath = Filename
        (self.Identification.FileRelativePath, self.Identification.FileName) = os.path.split(Filename)
        
        #
        # Init DecTable
        #
        #self.TblDec.Table = "Dec%s" % self.FileID
        #self.TblDec.Create()
        
        #
        # Init common datas
        #
        IfDefList, SectionItemList, CurrentSection, ArchList, ThirdList, IncludeFiles = \
        [], [], TAB_UNKNOWN, [], [], []
        LineNo = 0
        
        #
        # Parse file content
        #
        IsFindBlockComment = False
        ReservedLine = ''
        for Line in open(Filename, 'r'):
            LineNo = LineNo + 1
            #
            # Remove comment block
            #
            if Line.find(TAB_COMMENT_R8_START) > -1:
                ReservedLine = GetSplitValueList(Line, TAB_COMMENT_R8_START, 1)[0]
                IsFindBlockComment = True
            if Line.find(TAB_COMMENT_R8_END) > -1:
                Line = ReservedLine + GetSplitValueList(Line, TAB_COMMENT_R8_END, 1)[1]
                ReservedLine = ''
                IsFindBlockComment = False
            if IsFindBlockComment:
                continue

            #
            # Remove comments at tail and remove spaces again
            #
            Line = CleanString(Line)
            if Line == '':
                continue
            
            #
            # Find a new section tab
            # First insert previous section items
            # And then parse the content of the new section
            #
            if Line.startswith(TAB_SECTION_START) and Line.endswith(TAB_SECTION_END):
                #
                # Insert items data of previous section
                #
                Model = Section[CurrentSection.upper()]
                InsertSectionItems(Model, CurrentSection, SectionItemList, ArchList, ThirdList, self.RecordSet)
                #
                # Parse the new section
                #
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

                continue
            
            #
            # Not in any defined section
            #
            if CurrentSection == TAB_UNKNOWN:
                ErrorMsg = "%s is not in any defined section" % Line
                EdkLogger.error("Parser", PARSER_ERROR, ErrorMsg, File=Filename, Line=LineNo, RaiseError = EdkLogger.IsRaiseError)

            #
            # Add a section item
            #
            SectionItemList.append([Line, LineNo])
            # End of parse
        #End of For
        
        #
        # Insert items data of last section
        #
        Model = Section[CurrentSection.upper()]
        InsertSectionItems(Model, CurrentSection, SectionItemList, ArchList, ThirdList, self.RecordSet)
        
        #
        # Replace all DEFINE macros with its actual values
        #
        #ParseDefineMacro2(self.TblDec, self.RecordSet, GlobalData.gGlobalDefines)

    ## Transfer to Package Object
    # 
    # Transfer all contents of a Dec file to a standard Package Object
    #
    def DecToPackage(self):
        #
        # Init global information for the file
        #
        ContainerFile = self.Identification.FileFullPath
        
        #
        # Generate Package Header
        #
        self.GenPackageHeader(ContainerFile)
        
        #
        # Generate Includes
        # Only for R8
        #
        self.GenIncludes(ContainerFile)

        #
        # Generate Guids
        #
        self.GenGuidProtocolPpis(DataType.TAB_GUIDS, ContainerFile)

        #
        # Generate Protocols
        #
        self.GenGuidProtocolPpis(DataType.TAB_PROTOCOLS, ContainerFile)

        #
        # Generate Ppis
        #
        self.GenGuidProtocolPpis(DataType.TAB_PPIS, ContainerFile)
        
        #
        # Generate LibraryClasses
        #
        self.GenLibraryClasses(ContainerFile)
        
        #
        # Generate Pcds
        #
        self.GenPcds(ContainerFile)
    
    ## Get Package Header
    #
    # Gen Package Header of Dec as <Key> = <Value>
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenPackageHeader(self, ContainerFile):
        EdkLogger.debug(2, "Generate PackageHeader ...")
        #
        # Update all defines item in database
        #
        RecordSet = self.RecordSet[MODEL_META_DATA_HEADER]
        PackageHeader = PackageHeaderClass()
        OtherDefines = []
        for Record in RecordSet:
            ValueList = GetSplitValueList(Record[0], TAB_EQUAL_SPLIT)
            if len(ValueList) != 2:
                OtherDefines.append(Record[0])
            else:
                Name = ValueList[0]
                Value = ValueList[1]
                if Name == TAB_DEC_DEFINES_PACKAGE_NAME:
                    PackageHeader.Name = Value
                elif Name == TAB_DEC_DEFINES_PACKAGE_GUID:
                    PackageHeader.Guid = Value
                elif Name == TAB_DEC_DEFINES_PACKAGE_VERSION:
                    PackageHeader.Version = Value
                elif Name == TAB_DEC_DEFINES_DEC_SPECIFICATION:
                    PackageHeader.DecSpecification = Value
                else:
                    OtherDefines.append(Record[0])
            
        PackageHeader.FileName = self.Identification.FileName
        PackageHeader.FullPath = self.Identification.FileFullPath
        #PackageHeader.SupArchList = Record[1]
        self.Package.PackageHeader = PackageHeader
        UE = UserExtensionsClass()
        UE.Defines = OtherDefines
        self.Package.UserExtensions.append(UE)
        
    
    ## GenIncludes
    #
    # Gen Includes of Dec
    # 
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenIncludes(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_INCLUDES)
        Includes = {}
        #
        # Get all Includes
        #
        RecordSet = self.RecordSet[MODEL_EFI_INCLUDE]
        
        #
        # Go through each arch
        #
        for Record in RecordSet:
            Arch = Record[1]
            Key = Record[0]
            Include = IncludeClass()
            Include.FilePath = NormPath(Key)
            Include.SupArchList = Arch
            self.Package.Includes.append(Include)
    
    ## GenPpis
    #
    # Gen Ppis of Dec
    # <CName>=<GuidValue>
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenGuidProtocolPpis(self, Type, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % Type)
        Lists = {}
        #
        # Get all Items
        #
        RecordSet = self.RecordSet[Section[Type.upper()]]
        
        #
        # Go through each arch
        #
        for Record in RecordSet:
            Arch = Record[1]
            (Name, Value) = GetGuidsProtocolsPpisOfDec(Record[0], Type, ContainerFile, Record[2])
       
            ListMember = None
            if Type == TAB_GUIDS:
                ListMember = self.Package.GuidDeclarations
            elif Type == TAB_PROTOCOLS:
                ListMember = self.Package.ProtocolDeclarations
            elif Type == TAB_PPIS:
                ListMember = self.Package.PpiDeclarations
        
            ListClass = GuidProtocolPpiCommonClass()
            ListClass.CName = Name
            ListClass.Guid = Value
            ListClass.SupArchList = Arch
            ListMember.append(ListClass)
    
    ## GenLibraryClasses
    #
    # Gen LibraryClasses of Dec
    # <CName>=<GuidValue>
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenLibraryClasses(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_LIBRARY_CLASSES)
        LibraryClasses = {}
        #
        # Get all Guids
        #
        RecordSet = self.RecordSet[MODEL_EFI_LIBRARY_CLASS]
        
        #
        # Go through each arch
        #
        for Record in RecordSet:
            Arch = Record[1]
            List = GetSplitValueList(Record[0], DataType.TAB_VALUE_SPLIT)
            if len(List) != 2:
                continue
            LibraryClass = LibraryClassClass()
            LibraryClass.LibraryClass = List[0]
            LibraryClass.RecommendedInstance = NormPath(List[1])
            #LibraryClass.SupModuleList = SUP_MODULE_LIST
            LibraryClass.SupArchList = Arch
            self.Package.LibraryClassDeclarations.append(LibraryClass)
    
    def AddPcd(self, CName, Token, TokenSpaceGuidCName, DatumType, DefaultValue, ItemType, Arch):
        Pcd = PcdClass()
        Pcd.CName = CName
        Pcd.Token = Token
        Pcd.TokenSpaceGuidCName = TokenSpaceGuidCName
        Pcd.DatumType = DatumType
        Pcd.DefaultValue = DefaultValue
        Pcd.ItemType = ItemType
        Pcd.SupArchList = Arch
        self.Package.PcdDeclarations.append(Pcd)
    
    ## GenPcds
    #
    # Gen Pcds of Dec
    # <TokenSpcCName>.<TokenCName>|<Value>|<DatumType>|<Token>
    #
    # @param ContainerFile: The Dec file full path 
    #
    def GenPcds(self, ContainerFile):
        EdkLogger.debug(2, "Generate %s ..." % TAB_PCDS)
        Pcds = {}
        PcdToken = {}
        #
        # Get all Guids
        #
        RecordSet1 = self.RecordSet[MODEL_PCD_FIXED_AT_BUILD]
        RecordSet2 = self.RecordSet[MODEL_PCD_PATCHABLE_IN_MODULE]
        RecordSet3 = self.RecordSet[MODEL_PCD_FEATURE_FLAG]
        RecordSet4 = self.RecordSet[MODEL_PCD_DYNAMIC_EX]
        RecordSet5 = self.RecordSet[MODEL_PCD_DYNAMIC]
        
        #
        # Go through each arch
        #
        for Record in RecordSet1:
            Arch = Record[1]
            (TokenGuidCName, TokenName, DefaultValue, DatumType, Token, ItemType) = GetPcdOfDec(Record[0], TAB_PCDS_FIXED_AT_BUILD, ContainerFile, Record[2])
            self.AddPcd(TokenName, Token, TokenGuidCName, DatumType, DefaultValue, ItemType, Arch)
        for Record in RecordSet2:
            Arch = Record[1]
            (TokenGuidCName, TokenName, Value, DatumType, Token, Type) = GetPcdOfDec(Record[0], TAB_PCDS_PATCHABLE_IN_MODULE, ContainerFile, Record[2])
            self.AddPcd(TokenName, Token, TokenGuidCName, DatumType, DefaultValue, ItemType, Arch)
        for Record in RecordSet3:
            Arch = Record[1]
            (TokenGuidCName, TokenName, Value, DatumType, Token, Type) = GetPcdOfDec(Record[0], TAB_PCDS_FEATURE_FLAG, ContainerFile, Record[2])
            self.AddPcd(TokenName, Token, TokenGuidCName, DatumType, DefaultValue, ItemType, Arch)
        for Record in RecordSet4:
            Arch = Record[1]
            (TokenGuidCName, TokenName, Value, DatumType, Token, Type) = GetPcdOfDec(Record[0], TAB_PCDS_DYNAMIC_EX, ContainerFile, Record[2])
            self.AddPcd(TokenName, Token, TokenGuidCName, DatumType, DefaultValue, ItemType, Arch)
        for Record in RecordSet5:
            Arch = Record[1]
            (TokenGuidCName, TokenName, Value, DatumType, Token, Type) = GetPcdOfDec(Record[0], TAB_PCDS_DYNAMIC, ContainerFile, Record[2])
            self.AddPcd(TokenName, Token, TokenGuidCName, DatumType, DefaultValue, ItemType, Arch)
            
    ## Show detailed information of Package
    #
    # Print all members and their values of Package class
    #
    def ShowPackage(self):
        M = self.Package
        print 'Filename =', M.PackageHeader.FileName
        print 'FullPath =', M.PackageHeader.FullPath
        print 'BaseName =', M.PackageHeader.Name
        print 'Guid =', M.PackageHeader.Guid
        print 'Version =', M.PackageHeader.Version
        print 'DecSpecification =', M.PackageHeader.DecSpecification
        
#        for Arch in M.Header.keys():
#            print '\nArch =', Arch
#            print 'Filename =', M.Header[Arch].FileName
#            print 'FullPath =', M.Header[Arch].FullPath
#            print 'BaseName =', M.Header[Arch].Name
#            print 'Guid =', M.Header[Arch].Guid
#            print 'Version =', M.Header[Arch].Version
#            print 'DecSpecification =', M.Header[Arch].DecSpecification
        print '\nIncludes ='#, M.Includes
        for Item in M.Includes:
            print Item.FilePath, Item.SupArchList
        print '\nGuids ='#, M.GuidDeclarations
        for Item in M.GuidDeclarations:
            print Item.CName, Item.Guid, Item.SupArchList
        print '\nProtocols ='#, M.ProtocolDeclarations
        for Item in M.ProtocolDeclarations:
            print Item.CName, Item.Guid, Item.SupArchList
        print '\nPpis ='#, M.PpiDeclarations
        for Item in M.PpiDeclarations:
            print Item.CName, Item.Guid, Item.SupArchList
        print '\nLibraryClasses ='#, M.LibraryClassDeclarations
        for Item in M.LibraryClassDeclarations:
            print Item.LibraryClass, Item.RecommendedInstance, Item.SupModuleList, Item.SupArchList
        print '\nPcds ='#, M.PcdDeclarations
        for Item in M.PcdDeclarations:
            print 'CName=', Item.CName, 'TokenSpaceGuidCName=', Item.TokenSpaceGuidCName, 'DefaultValue=', Item.DefaultValue, 'ItemType=', Item.ItemType, 'Token=', Item.Token, 'DatumType=', Item.DatumType, Item.SupArchList
        print '\nUserExtensions ='
        for Item in M.UserExtensions:
            print Item.Defines

##
#
# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
#
if __name__ == '__main__':
    EdkLogger.Initialize()
    EdkLogger.SetLevel(EdkLogger.QUIET)
    
    W = os.getenv('WORKSPACE')
    F = os.path.join(W, 'Nt32Pkg/Nt32Pkg.dec')

    P = Dec(os.path.normpath(F), True, W)
    P.ShowPackage()