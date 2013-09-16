#!/usr/local/bin/python
# -*- coding: utf-8 -*-

__author__ = 'Matthew'

import json
import glob
import struct
import xml.dom.minidom
import msmt


class TranslateText(object):
    def __init__(self, settings):
        self.token = msmt.get_access_token(settings['msmt_client_id'], settings['msmt_client_secret'])

    def translate(self, text, to_lang, from_lang=None):
        return self.parse_xml(msmt.translate(self.token, text, to_lang, from_lang))

    def parse_xml(self, s):
        dom = xml.dom.minidom.parseString(s)
        if dom.documentElement.tagName != 'string':
            return None
        if len(dom.documentElement.childNodes) != 1:
            return None
        if dom.documentElement.childNodes[0].nodeType != dom.documentElement.childNodes[0].TEXT_NODE:
            return None

        return dom.documentElement.childNodes[0].data.encode('utf-8')


class LogFileCollection(object):
    def __init__(self, settings):
        self.settings = settings
        for filename in self.find_log_files():
            LogFileParser(self.settings, open(filename, 'rb'))

    def find_log_files(self):
        return glob.glob(self.settings['ffxivarr_log_directoy'] + '/*.log')


class LogFileParser(object):
    def __init__(self, settings, fp):
        self.settings = settings
        self.parse(fp)

    def parse(self, fp):
        header_format = '=ii'
        (index_start, index_end) = struct.unpack(header_format, fp.read(struct.calcsize(header_format)))
        #print index_start, index_end, index_end - index_start

        # offsets are relative to the end of the header (index_start + index_end + index_data*1000)
        data_start_offset = struct.calcsize('i') * (2 + (index_end - index_start))

        entries = {}
        entry_length_format = '=i'
        last_offset = 0
        for index in range(0, index_end - index_start):
            this_offset = struct.unpack(entry_length_format, fp.read(struct.calcsize(entry_length_format)))[0]
            entries[index] = {'offset': data_start_offset + last_offset,
                              'length': (this_offset - last_offset),
                              'data':   None}
            # print index, '=>', entries[index]
            last_offset = this_offset

        for index in entries:
            entries[index]['data'] = self.parse_entry(fp, entries[index]['offset'], entries[index]['length'])

            #if entries[index]['data']['type'] not in [57, 65, 66, 67, 68, 69, 70]:
            #    print entries[index]['data']

            # Unknown is entry type?
            # 48 = Say or Party
            # 49 = Emotes
            # 50 = ?  (effects, damage, pet casts)
            # 51 = Self messages
            # 52 = ?  (level ups, self exp gains, npc chat)
            # 65 = ?  (takes damage, and some buffs)
            # 66 = ?  (things being defeated)
            # 67 = Attrib reset only entry

            # if entries[index]['data']['unknown'] == 48:
            #     print entries[index]['data']

            global translate

            if entries[index]['data']['unknown'] == 48:
                items = entries[index]['data']['text'].split(':')

                # normal message, not system or whisper
                if len(items) == 2:
                    (person, message) = items

                    if '\x02.' in message:
                        message = '(skipped due to auto translate)'

                    if '\xe3' in message:
                        try:
                            message.decode('utf-8')
                            message = message + " <=> " + translate.translate(message, 'en', 'ja')
                        except Exception, e:
                            print e
                            message = '(Invalid utf-8 aborted)'
                            pass

                    print  message

    def parse_entry(self, fp, offset, length):
        fp.seek(offset)
        entry_format = '=10sbb2s' + str(length - 14) + 's'
        (uid, unknown, entry_type, colons, text) = struct.unpack(entry_format, fp.read(struct.calcsize(entry_format)))

        return {'uid': uid, 'unknown': unknown, 'type': entry_type, 'text': text}


settings = json.load(open('settings.json'))

translate = TranslateText(settings)
collection = LogFileCollection(settings)