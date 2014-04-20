#!/usr/bin/env python
#
# Copyright (c) 2014, Arista Networks, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#  - Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#  - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#  - Neither the name of Arista Networks nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# SQLLite integration
#
#    Version 1.0 4/19
#    Written by:
#       Andrei Dvornic, Arista Networks
#
#    Revision history:
#       1.0 - initial release
#       2.0 - turn off interface if error condition persists
#           - syslog on degradation
#           - removed email notifications
#       3.0 - use eAPI for polling interface counters
#           - configuration at the top of the script

__author__ = 'loceur'

'''
    DESCRIPTION
        This script provides a template and example to save data taken from
        eAPI and store it in the existing sqllite3 db found on an Arista
        switch.  This data can then be accessed from the CLI with aliases
        and the direct sql commands.

    INSTALLATION

    CONFIGURATION/DEBUGGING

    COMPATIBILITY

    LIMITATIONS

'''

import sqlite3
import jsonrpclib
import optparse
from ctypes import cdll, byref, create_string_buffer





#-------------------Configuration------------------------
EAPI_USERNAME = 'admin'
EAPI_PASSWORD = 'password'
EAPI_ENABLE_PASSWORD = ''

# http/https
EAPI_METHOD = 'http'

# How often to poll for information (seconds)
EAPI_POLL_INTERVAL = 5       # in seconds

#--------------------------------------------------------

class ConnectionError( Exception ):
    '''
    Raised when connection to a eAPI or DB server cannot
    be established.
    '''
    pass

class EApiClient( object ):

    def __init__( self ):
        url = '%s://%s:%s@localhost/command-api' % \
              ( EAPI_METHOD, EAPI_USERNAME, EAPI_PASSWORD )
        self.client = jsonrpclib.Server( url  )

        try:
            self.runEnableCmds( [] )
        except socket.error:
            raise ConnectionError( url )

    def runEnableCmds( self, cmds, mode='json' ):
        result = self.client.runCmds(
            1, [ { 'cmd': 'enable',
                   'input': EAPI_ENABLE_PASSWORD } ] +
            cmds, mode)[ 1: ]

        if mode == 'text':
            return [ x.values()[ 0 ] for x in result ]
        else:
            return result

    def connectedInterfaces( self ):
        # Using text mode in order to be able to match interface shortname
        # in interfaceErrorCounters
        output = self.runEnableCmds(
            [ 'show interfaces status connected' ],
            mode='text' )[ 0 ].split( '\n' )[ 1 : -1 ]
        return [ x.split()[ 0 ] for x in output ]

    def interfaceErrorCounters( self, interfaces ):
        result = {}
        output = self.runEnableCmds(
            [ 'show interfaces counters errors' ],
            # Not yet converted
            mode='text' )[ 0 ].split( '\n' )[ 1 : -1 ]
        for line in output:
            tokens = line.split()
            if tokens[ 0 ] in interfaces:
                result[ tokens[ 0 ] ] = { 'fcs': int( tokens[ 1 ] ),
                                          'symbol': int( tokens[ 3 ] ) }
        return result

    def connectedInterfacesCounters( self ):
        return self.interfaceErrorCounters( self.connectedInterfaces() )

    def turnOffInterface( self, interface ):
        self.runEnableCmds( self, [ 'configure',
                                    'interface %s' % interface,
                                    'shutdown' ] )

def setProcName(newname):
    libc = cdll.LoadLibrary( 'libc.so.6' )
    buff = create_string_buffer( len( newname ) + 1 )
    buff.value = newname
    libc.prctl( 15, byref( buff ), 0, 0, 0)

class sqlAristaDB( object):

    '''
    Wrapper class for the sqlite3 specifically connecting to the local Arista sqllite DB
    '''
    def __init__( self ):
        # Will need to connect to existing sqllite db
        # fail if not

        try:
            self.dbConn = sqlite3.connect("/tmp/eventMon.db")
        except:
            raise ConnectionError()

    def createTable( self, tableName ):
        '''
        Creates a new table in the db
        '''

        #CREATE TABLE tableName IF NOT EXIST
        # May want error case if table exists.  For now, we ignore.
        self.dbConn.execute("CREATE TABLE IF NOT EXISTS "+  tableName)
        self.dbConn.commit()

    def removeTable (self, tableName ):
        '''
        Deletes a table in the db
        '''

        self.dbConn.execute("DROP TABLE IF EXISTS "+ tableName)
        self.dbConn.commit()


    def insertRow ( self, list, table ):
        '''
        Insert a row into an existing table
        '''

        #INSERT INTO table VALUES (?), list
        pass

    def searchTable ( self, list, table):
        '''
        Search for a particular
        '''
        #Do I need to implement this?
        pass


def main():
    global debug

    setProcName( 'json2sql' )

    # Create help string and parse cmd line
    usage = 'usage: %prog [options]'
    op = optparse.OptionParser(usage=usage)
    op.add_option( '-d', '--debug', dest='debug', action='store_true',
                   help='print debug info' )
    opts, _ = op.parse_args()

    debug = opts.debug
    db = sqlAristaDB()
    db.createTable("test(x)")
    db.removeTable("test")
    #syslog.openlog( 'phm', 0, syslog.LOG_LOCAL4 )

    #checkInterfaces()

if __name__ == '__main__':
   main()