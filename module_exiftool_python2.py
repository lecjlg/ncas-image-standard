# module_exiftool
#
# Python handler for ExifTool image metadata software
#
# Copies of this software and its documenttaion are openly-accessible from 
#   https://github.com/dahooper/exiftool-handler
# 
# Last updated 2022/10/12
#
import datetime, os, platform, subprocess, string, sys, textwrap, yaml
#
###
#
class Handler():
    def __init__(self):
        self.variables = {
            "no_general_error_has_been_registered": True ,
            "no_template_error_has_been_registered": True ,
            "string_types": [str],
            "standard_exiftool_extraction_arguments": [
                "exiftool", "-G1", "-j", "-c"],
            "gps_extraction_formats": {
                "+D": "%+.6f", 
                "+DM": "%+d %+.4f", 
                "+DMS": "%+d %+d %+.2f",
                "D": "%.6f", 
                "DM": "%d %.4f", 
                "DMS": "%d %d %.2f"},
            "standard_tag_names": [
                "XMP-xmp:MetadataDate", "XMP-xmp:ModifyDate"],
            "global_substitution_keys": ["__utcnow__", "__utcnowstr__"],
            "datetime_format": {
                "none": "{:%Y:%m:%d %H:%M:%S}",
                "Z": "{:%Y:%m:%d %H:%M:%S}Z"},
            "prohibited_template_ids": ["__latest__", "__input__"],
            "templates": {},
            "source_of_metadata": {},
            "unrecognised_tags": {"extracted": []},
            "metadata_datetime": {},
            "metadata_datetime_string": {},
            "python_version": sys.version_info[0],
            "display_wrapped_line_format": "    {}",
            "operating_system": platform.system()
        }
#
###
#
# Python 2: unblock the following code line
# Python 3:   block the following code line
#
        self.variables["string_types"].append(unicode)
#
###
#
        self.options = {
            "allow_unrecognised_tags": {
                "permissible_values": [False, True],
                "value": False},
            "allow_tag_overwrites": {
                "permissible_values": [False, True],
                "value": False},
            "add_standard_tags": {
                "permissible_values": [False, True],
                "value": True},
            "gps_extraction": {
                "permissible_values": ["D", "+D", "DM", "+DM", "DMS", "+DMS"],
                "value": "+D"},
            "timezone_indicator": {
                "permissible_values": ["none", "Z"],
                "value": "none"},
            "verbosity_level": {
                "permissible_values": [0, 1, 2, 3],
                "value": 1},
            "show_data_types": {
                "permissible_values": [False, True],
                "value": True} }

        self.variables["display_order_of_options"] = \
            sorted ( self.options.keys() )
        maximum_length_of_option_name = 0
        for option_name in self.variables["display_order_of_options"]:
            length_of_option_name = len(option_name)
            if length_of_option_name > maximum_length_of_option_name:
                maximum_length_of_option_name = length_of_option_name
        self.variables["show_options_format"] = \
            " {:>" + str(maximum_length_of_option_name) + "}: {:<5} {}"

        self.handlers = {
            "indented_message": textwrap.TextWrapper(
                width = 78,
                initial_indent = "",
                subsequent_indent = "  "),
            "unindented_message": textwrap.TextWrapper(
                width = 78,
                initial_indent = "",
                subsequent_indent = ""),
            "string": string.Formatter()}

        self.metadata = {"extracted": {}, "prepared": {}}
        self.templates = {}

        self.load_recognised_tags()
#
###
#
    def register_a_general_error(self, function_name, message):
        self.variables["no_general_error_has_been_registered"] = False
        if self.options["verbosity_level"]["value"] > 0:
            expanded_message = "\033[1mGENERAL ERROR\033[0m {}.{}.{}(). {}".format(
                self.__class__.__module__, 
                self.__class__.__name__, 
                function_name, 
                message)
            print(self.handlers["indented_message"].fill(expanded_message))
#
###
#
    def register_a_template_error(self, function_name, message):
        self.variables["no_template_error_has_been_registered"] = False
        if self.options["verbosity_level"]["value"] > 0:
            expanded_message = "\033[1mTEMPLATE ERROR\033[0m {}.{}.{}(). {}".format(
                self.__class__.__module__, 
                self.__class__.__name__, 
                function_name, 
                message)
            print(self.handlers["indented_message"].fill(expanded_message))
#
###
#
    def show_a_warning_message(self, function_name, message):
        if self.options["verbosity_level"]["value"] > 0:
            expanded_message = "\033[1mWARNING\033[0m {}.{}.{}(). {}".format(
                self.__class__.__module__, 
                self.__class__.__name__, 
                function_name, 
                message)
            print(self.handlers["indented_message"].fill(expanded_message))
#
###
#
    def show_options(self):
        print("")
        print(self.variables["show_options_format"].format(
            "Option", "Value", "Permissible Values"))
        print(self.variables["show_options_format"].format(
            "------", "-----", "------------------"))
        for option_name in self.variables["display_order_of_options"]:
              print(self.variables["show_options_format"].format(
                  option_name,
                  self.options[option_name]["value"],
                  self.options[option_name]["permissible_values"]))

        print("")
#
###
#
    def set_option(self, option_name, option_value):
        function_name = "set_option"
        self.variables["no_general_error_has_been_registered"] = True

        if option_name not in self.options:
            self.register_a_general_error(
                function_name, 
                'An unrecognised option name was supplied.')
            self.show_options()

        elif option_value not in self.options[option_name]["permissible_values"]:
            self.register_a_general_error(
                function_name, 
                'The supplied value for option "{}" is not permissible.'.format(option_name))
            self.show_options()

        else:
            self.options[option_name]["value"] = option_value
#
###
#
    def load_recognised_tags(self):
        function_name = "load_recognised_tags"

        self.variables["no_general_error_has_been_registered"] = True
        self.variables["tag_supports_multiple_values"] = {}
        self.variables["full_tag_name_for_unambiguous_short_tag_name"] = {}
        self.variables["group_name_for_unambiguous_short_tag_name"] = {}
        self.variables["group_names_for_ambiguous_short_tag_name"] = {}

        final_character_index = __file__ .rfind("_python")
        source_file_path = __file__[:final_character_index] + "_recognised_tags.dat"
        if not os.path.isfile(source_file_path):
            self.register_a_general_error(function_name, 'Source file "{}" is not available.'.format(source_file_path))
        else:
            source_file = open(source_file_path, "r")
            source_file_contents = source_file.readlines()
            source_file.close()
            line_number = 1
            for source_file_line in source_file_contents:
                if not source_file_line.startswith("#"):
                    stripped_value = source_file_line.strip()
                    if stripped_value.startswith("+"):
                        tag_supports_multiple_values = True
                        full_tag_name =  stripped_value[1:].lstrip()
                    else:
                        tag_supports_multiple_values = False
                        full_tag_name =  stripped_value

                    if full_tag_name != "":
                        if " " in full_tag_name:
                            self.register_a_general_error(
                                function_name, 
                                'The full tag name "{}" given on line {} is invalid since it contains a space.'.format(full_tag_name, line_number))

                        number_of_colons = full_tag_name.count(":")
                        if number_of_colons != 1:
                            self.register_a_general_error(
                                function_name, 
                                'The full tag name "{}" given on line {} is invalid since it contains {} colons. Only 1 is permissible.'.format(full_tag_name, line_number, number_of_colons))

                        self.variables["tag_supports_multiple_values"][full_tag_name] = tag_supports_multiple_values

                line_number += 1

        if self.variables["no_general_error_has_been_registered"]:
            for full_tag_name in self.variables["tag_supports_multiple_values"]:
                group_name, short_tag_name = full_tag_name.split(":")

                if short_tag_name in self.variables["full_tag_name_for_unambiguous_short_tag_name"]:                
                    self.variables["group_names_for_ambiguous_short_tag_name"][short_tag_name] = [group_name, self.variables["group_name_for_unambiguous_short_tag_name"].pop(short_tag_name)]
                    del self.variables["full_tag_name_for_unambiguous_short_tag_name"][short_tag_name]

                elif short_tag_name in self.variables["group_names_for_ambiguous_short_tag_name"]:
                    self.variables["group_names_for_ambiguous_short_tag_name"][short_tag_name].append(group_name)

                else:
                    self.variables["full_tag_name_for_unambiguous_short_tag_name"][short_tag_name] = full_tag_name
                    self.variables["group_name_for_unambiguous_short_tag_name"][short_tag_name] = group_name

            for short_tag_name in self.variables["group_names_for_ambiguous_short_tag_name"]:
                self.variables["group_names_for_ambiguous_short_tag_name"][short_tag_name].sort()

            self.variables["recognised_tags_order"] = \
                sorted( self.variables["tag_supports_multiple_values"].keys() )

        else:
            self.variables["tag_supports_multiple_values"] = {}
            self.variables["full_tag_name_for_unambiguous_short_tag_name"] = {}
            self.variables["group_name_for_unambiguous_short_tag_name"] = {}
            self.variables["group_names_for_ambiguous_short_tag_name"] = {}
#
###
#
    def show_recognised_tags(self):
        print("")
        print("This software recognises the following tag names.")
        print("- The letter \033[1mA\033[0m incates that the short tag name is ambiguous")
        print("  and so the full tag name must be used. Otherwise either")
        print("  the short or the full tag name may be used.")
        print('- A "+" sign indicates a list tag, which may take multiple values.')
        print("")

        for full_tag_name in self.variables["recognised_tags_order"]:
            if self.variables["tag_supports_multiple_values"][full_tag_name]:
                multiple_values_indicator = "+"
            else:
                multiple_values_indicator = " "

            group_name, short_tag_name = full_tag_name.split(":")
            if short_tag_name in self.variables["group_name_for_unambiguous_short_tag_name"]:
                print("  {} {}:\033[1m{}\033[0m".format(
                    multiple_values_indicator, group_name, short_tag_name))
            else:
                print("\033[1mA\033[0m {} \033[1m{}:{}\033[0m".format(
                    multiple_values_indicator, group_name, short_tag_name))

        print("")
#
###
#
    def load_a_template(self, file_path):
        function_name = "load_a_template"

        self.variables["no_template_error_has_been_registered"] = True
        self.variables["templates"]["__latest__"] = {
            "template_id": "",
            "supplied_tag_name_for_entry": [],
            "full_tag_name_for_entry": [],
            "entry_indices_of_unrecognised_tags": [],
            "usage_details_for_substitution_key": {}}

        if not os.path.isfile(file_path):
            self.register_a_general_error(
                function_name, 
                'Supplied file path "{}" is invalid.'.format(file_path))
        else:
            self.variables["templates"]["__latest__"]["file_path"] = \
                os.path.abspath(file_path)
            self.variables["templates"]["__latest__"]["file_name"] = \
                os.path.basename(file_path)
            try:
                self.templates["__latest__"] = yaml.load(
                    open(file_path, "r"), 
                    Loader=yaml.SafeLoader)
            except yaml.YAMLError as exception_message:
                self.register_a_template_error(
                    function_name, 
                    "Template file failed yaml parsing.")
                print(exception_message)
            else:
                self.check_latest_template_for_conformity()

        if self.variables["no_template_error_has_been_registered"]:
            self.scan_latest_template_for_substitutions()
            template_id = \
                self.variables["templates"]["__latest__"]["template_id"]
            self.templates[template_id] = \
                self.templates.pop("__latest__")
            self.variables["templates"][template_id] = \
                self.variables["templates"].pop("__latest__")

            number_of_unrecognised_tags = len(self.variables["templates"][template_id]["entry_indices_of_unrecognised_tags"])
            if number_of_unrecognised_tags > 0:
                self.show_a_warning_message(
                    function_name,
                    '{} unrecognised tags have been given in template "{}". These cannot be used to embed unless a relevant entry is given in the accompanying file "module_exiftool_recognised_tags.dat".'.format(
                        number_of_unrecognised_tags,
                        template_id))
                unrecognised_tag_number = 1
                for entry_index in self.variables["templates"][template_id]["entry_indices_of_unrecognised_tags"]:
                    print("     [{}] {}".format(
                        unrecognised_tag_number,
                        self.variables["templates"][template_id]["supplied_tag_name_for_entry"][entry_index]))

                    unrecognised_tag_number += 1

            return template_id
        else:
            return ""
#
###
#
# Internal function for checking whether the template conforms to the expected
# structure.
#
    def check_latest_template_for_conformity(self):
        function_name = "check_latest_template_for_conformity"

        if type(self.templates["__latest__"]) != list:
            self.register_a_template_error(
                function_name, 
                "Template does not conform to a list.")
        else:
            number_of_entries = len(self.templates["__latest__"])
            entry_index = 0
            while entry_index < number_of_entries:
                entry_number = entry_index + 1
                if type(self.templates["__latest__"][entry_index]) != dict:
                    self.register_a_template_error(
                        function_name, 
                        "Entry number {} is not of the required key: value format.".format(
                            entry_number))
                else:
                    number_of_entry_keys = len(self.templates["__latest__"][entry_index])
                    if number_of_entry_keys != 1:
                        self.register_a_template_error(
                            function_name, 
                            "Entry number {} has {} keys. Only 1 is expected.".format(
                                entry_number, 
                                number_of_entry_keys))
                    else:
                        for supplied_tag_name in self.templates["__latest__"][entry_index]:
                            continue

                        if supplied_tag_name == "template_id":
                            template_id = self.templates["__latest__"][entry_index][supplied_tag_name]
                            if type(template_id) not in self.variables["string_types"]:
                                self.register_a_template_error(
                                    function_name, 
                                    'The value supplied for "template_id" (entry {}) is not of string type.'.format(
                                        entry_number))

                            if template_id in self.variables["prohibited_template_ids"]:
                                self.register_a_template_error(
                                    function_name, 
                                    'The value "{}" supplied for "template_id" (entry {}) is not permitted.'.format(
                                        template_id, 
                                        entry_number))


                            if self.variables["templates"]["__latest__"]["template_id"] != "":
                                self.register_a_template_error(
                                    function_name, 
                                    'Entry {} contains a repeat instance of "template_id".'.format(
                                        entry_number))

                            if template_id in self.templates:
                                self.register_a_template_error(
                                    function_name, 
                                    'A template with identifier "{}" has already been loaded.'.format(
                                        template_id))

                            self.variables["templates"]["__latest__"]["template_id"] = template_id
                            self.variables["templates"]["__latest__"]["full_tag_name_for_entry"].append(supplied_tag_name)
                            self.variables["templates"]["__latest__"]["supplied_tag_name_for_entry"].append(supplied_tag_name)

                        else:
                            self.determine_supplied_tag_name_details(
                                supplied_tag_name)
                            self.determine_tag_value_details(self.templates["__latest__"][entry_index][supplied_tag_name])

                            if not self.variables["supplied_tag_name_is_valid"]:
                                self.register_a_template_error(
                                    function_name, 
                                    "Entry {}. {}".format(
                                        entry_number, 
                                        self.variables["reason_for_supplied_tag_name_invalidity"]))

                            if self.variables["supplied_tag_name_is_recognised"]:
                                if self.variables["tag_value_contains_multiple_values"] and (not self.variables["supplied_tag_name_supports_multiple_values"]):
                                    self.register_a_template_error(
                                        function_name, 
                                        'Tag "{}" (entry {}) does not support multiple values.'.format(
                                            supplied_tag_name, 
                                            entry_number))
                            else:
                                self.variables["templates"]["__latest__"]["entry_indices_of_unrecognised_tags"].append(entry_index)

                            if supplied_tag_name in self.variables["templates"]["__latest__"]["supplied_tag_name_for_entry"]:
                                self.register_a_template_error(
                                    function_name, 
                                    'Entry number {} contains a repeat for supplied tag name "{}".'.format(
                                        entry_number, 
                                        supplied_tag_name))

                            if self.variables["full_tag_name_for_supplied_tag_name"] in self.variables["templates"]["__latest__"]["full_tag_name_for_entry"]:
                                self.register_a_template_error(
                                    function_name, 
                                    'Entry {} ({}) contains a repeat definition for full tag name "{}".'.format(
                                        entry_number, 
                                        supplied_tag_name, 
                                        self.variables["full_tag_name_for_supplied_tag_name"]))

                            if not self.variables["supplied_tag_value_is_valid"]:
                                self.register_a_template_error(
                                    function_name, 
                                    'Value for supplied tag name "{}" (entry {}) is not of string type.'.format(
                                        supplied_tag_name, 
                                        entry_number))
                                
                            self.variables["templates"]["__latest__"]["full_tag_name_for_entry"].append(self.variables["full_tag_name_for_supplied_tag_name"])
                            self.variables["templates"]["__latest__"]["supplied_tag_name_for_entry"].append(supplied_tag_name)

                entry_index += 1

            if self.variables["templates"]["__latest__"]["template_id"] == "":
                self.register_a_template_error(
                    function_name, 
                    'No "template_id" entry has been found.')
#
###
#
    def determine_supplied_tag_name_details(self, supplied_tag_name):
        self.variables["supplied_tag_name"] = supplied_tag_name

        if type(supplied_tag_name) not in self.variables["string_types"]:
            self.variables["supplied_tag_name_is_valid"] = False
            self.variables["reason_for_supplied_tag_name_invalidity"] = 'The supplied tag name is not of a string type.'
            self.variables["supplied_tag_name_is_recognised"] = False
            self.variables["full_tag_name_for_supplied_tag_name"] = ""
        else:
            number_of_colons = supplied_tag_name.count(":")
            if " " in supplied_tag_name:
                self.variables["supplied_tag_name_is_valid"] = False
                self.variables["reason_for_supplied_tag_name_invalidity"] = 'The supplied tag name "{}" contains at least one space. None is allowed.'.format(supplied_tag_name)
                self.variables["supplied_tag_name_is_recognised"] = False
                self.variables["full_tag_name_for_supplied_tag_name"] = ""
            elif number_of_colons == 0:
                self.variables["supplied_tag_name_type"] = "short"
                self.variables["short_tag_name_for_supplied_tag_name"] = \
                    supplied_tag_name
                if supplied_tag_name in self.variables["full_tag_name_for_unambiguous_short_tag_name"]:

                    self.variables["supplied_tag_name_is_valid"] = True 
                    self.variables["supplied_tag_name_is_recognised"] = True
                    self.variables["full_tag_name_for_supplied_tag_name"] = \
                        self.variables["full_tag_name_for_unambiguous_short_tag_name"][supplied_tag_name]
                
                elif supplied_tag_name in self.variables["group_names_for_ambiguous_short_tag_name"]:

                    self.variables["supplied_tag_name_is_valid"] = False
                    self.variables["reason_for_supplied_tag_name_invalidity"] = 'Supplied short tag name "{}" is ambiguous since it can be associated with more than one group.'.format(supplied_tag_name)
                    self.variables["supplied_tag_name_is_recognised"] = False
                    self.variables["full_tag_name_for_supplied_tag_name"] = ""

                else:
                    self.variables["supplied_tag_name_is_valid"] = True
                    self.variables["supplied_tag_name_is_recognised"] = False
                    self.variables["full_tag_name_for_supplied_tag_name"] = \
                        "UNKNOWN:" + supplied_tag_name

            elif number_of_colons == 1:
                self.variables["supplied_tag_name_type"] = "full"
                self.variables["full_tag_name_for_supplied_tag_name"] = \
                    supplied_tag_name

                if supplied_tag_name in self.variables["tag_supports_multiple_values"]:
                    self.variables["supplied_tag_name_is_valid"] = True
                    self.variables["supplied_tag_name_is_recognised"] = True
                else:
                    self.variables["supplied_tag_name_is_recognised"] = False
                    self.variables["supplied_tag_name_is_valid"] = True

            else:
                self.variables["supplied_tag_name_type"] = "unknown"
                self.variables["full_tag_name_for_supplied_tag_name"] = ""
                self.variables["supplied_tag_name_is_valid"] = False
                self.variables["reason_for_supplied_tag_name_invalidity"] = 'The supplied tag name "{}" contains more than one instance of ":". Only 1 is allowed.'.format(supplied_tag_name)

        if ((self.variables["full_tag_name_for_supplied_tag_name"] in 
             self.variables["tag_supports_multiple_values"]) or 
            ((not self.variables["supplied_tag_name_is_recognised"]) and 
             self.variables["supplied_tag_name_is_valid"])):

            self.variables["supplied_tag_name_supports_multiple_values"] = True
        else:
            self.variables["supplied_tag_name_supports_multiple_values"] = False
#
###
#
    def determine_tag_value_details(self, tag_value):
        self.variables["supplied_tag_value_is_valid"] = True
        data_type = type(tag_value)
        if data_type == list:
            self.variables["tag_value_contains_multiple_values"] = True
            for sub_value in tag_value:
                if type(sub_value) not in self.variables["string_types"]:
                    self.variables["supplied_tag_value_is_valid"] = False
        else:
            self.variables["tag_value_contains_multiple_values"] = False
            if data_type not in self.variables["string_types"]:
                self.variables["supplied_tag_value_is_valid"] = False
#
###
#
    def scan_latest_template_for_substitutions(self):
        entry_index = 0
        while entry_index < len(self.variables["templates"]["__latest__"]["supplied_tag_name_for_entry"]):
            supplied_tag_name = self.variables["templates"]["__latest__"]["supplied_tag_name_for_entry"][entry_index] 
            if supplied_tag_name != "template_id":
                value_type = type(self.templates["__latest__"][entry_index][supplied_tag_name])
                if value_type == list:
                    for sub_value in self.templates["__latest__"][entry_index][supplied_tag_name]:
                        self.scan_tag_value_for_substitutions(
                            supplied_tag_name, 
                            sub_value)

                else:
                    self.scan_tag_value_for_substitutions(
                        supplied_tag_name, 
                        self.templates["__latest__"][entry_index][supplied_tag_name])

            entry_index += 1
#
###
#
    def scan_tag_value_for_substitutions(self, supplied_tag_name, tag_value):
        for text_fragment in self.handlers["string"].parse(tag_value):
            if text_fragment[1] != None:
                substitution_key = text_fragment[1]
                usage_details = 'Supplied tag name "{}", format "{}"'.format(supplied_tag_name, text_fragment[2])
                if substitution_key not in self.variables["templates"]["__latest__"]["usage_details_for_substitution_key"]:

                    self.variables["templates"]["__latest__"]["usage_details_for_substitution_key"][substitution_key] = [usage_details]

                elif usage_details not in self.variables["templates"]["__latest__"]["usage_details_for_substitution_key"][substitution_key]:

                    self.variables["templates"]["__latest__"]["usage_details_for_substitution_key"][substitution_key].append(usage_details)
#
###
#
    def show_templates_available(self):
        print("")
        number_of_templates = len(self.variables["templates"])
        if number_of_templates == 0:
            print("No templates have been loaded yet.")
        else:
            print("{} templates have been loaded:".format(number_of_templates))

            template_ids = sorted( self.variables["templates"].keys() )
            maximum_template_id_length = 0
            for template_id in template_ids:
                template_id_length = len(template_id)
                if template_id_length > maximum_template_id_length:
                    maximum_template_id_length = template_id_length
                
            display_format = \
                '  "{:>' + str(maximum_template_id_length) + '}" from file "{}"'
            for template_id in template_ids:
                print(display_format.format(template_id, self.variables["templates"][template_id]["file_name"]))

        print("")
#
###
#
    def show_template_requirements(self, template_id):
        function_name = "show_template_requirements"
        self.variables["no_general_error_has_been_registered"] = True
        
        if template_id not in self.variables["templates"]:
            self.register_a_general_error(
                function_name, 
                'Supplied template identifier is not recognised.'.format(template_id))
            
        if self.variables["no_general_error_has_been_registered"]:
            print("")
            if len(self.variables["templates"][template_id]["usage_details_for_substitution_key"]) == 0:

                print(self.handlers["unindented_message"].fill('Metadata template "{}" does not require any substitutions.'.format(template_id)))

            else:
                print(self.handlers["unindented_message"].fill('Metadata template \033[1m{}\033[0m uses substitutions in the following ways:'.format(template_id)))
                print("")
                
                substitution_keys = sorted( self.variables["templates"][template_id]["usage_details_for_substitution_key"].keys() )
                for substitution_key in substitution_keys:
                    print("  \033[1m{}\033[0m".format(substitution_key))
                    for usage_details in self.variables["templates"][template_id]["usage_details_for_substitution_key"][substitution_key]:
                        print("    {}".format(usage_details))

            print("")
#
###
#
    def return_file_path_for_os(self, supplied_file_path):
        if self.variables["operating_system"].startswith("CYGWIN"):
            file_path_for_os = subprocess.check_output(
                ["cygpath", "-w", supplied_file_path]).rstrip()
        else:
            file_path_for_os = supplied_file_path

        return file_path_for_os
#
###
#
    def return_datetime_string(self, supplied_datetime):
        timezone_indicator_option = self.options["timezone_indicator"]["value"]
        datetime_string = self.variables["datetime_format"][
            timezone_indicator_option].format(supplied_datetime)

        return datetime_string
#
###
#
    def display(self, option="extracted", output_file_path=None):
        function_name = "display"
        self.variables["no_general_error_has_been_registered"] = True

        if option in self.metadata:
            metadata_type = option
            if self.metadata[metadata_type] == {}:
                self.register_a_general_error(
                    function_name, 
                    'Metadata are not available for supplied type "{}".'.format(metadata_type))

        elif type(option) in self.variables["string_types"]:
            if option.startswith("~"):
                absolute_source_file_path = os.path.expanduser(option)
            else:
                absolute_source_file_path = os.path.abspath(option)
            if os.path.isfile(absolute_source_file_path):
                metadata_type = "extracted"
                self.extract(absolute_source_file_path, False)
                if self.metadata["extracted"] == {}:
                    self.register_a_general_error(
                        function_name, 
                        'Metadata could not be extracted from the supplied file path "{}".'.format(absolute_source_file_path))
            else:
                self.register_a_general_error(
                    function_name, 
                    'The supplied source file path "{}" is invalid.'.format(
                        option))
        else:
            self.register_a_general_error(
                function_name, 
                'Supplied option "{}" is not recognised. It must either be an image file path or one of the following: {}.'.format(option, self.metadata.keys()))

        if type(output_file_path) in self.variables["string_types"]:
            if output_file_path.startswith("~"):
                absolute_source_file_path = os.path.expanduser(output_file_path)
            else:
                absolute_output_file_path = os.path.abspath(output_file_path)
            output_file_directory_path = \
                os.path.dirname(absolute_output_file_path)
            if not os.path.isdir(output_file_directory_path):
                self.register_a_general_error(
                    function_name, 
                    'The supplied output file path "{}" refers to an invalid directory.'.format(absolute_output_file_path))

            if os.path.isfile(absolute_output_file_path):
                self.show_a_warning_message(
                    function_name, 
                    'Output file "{}" is being overwritten.'.format(
                        absolute_output_file_path))

        if self.variables["no_general_error_has_been_registered"]:
            if output_file_path != None:
                print('Redirecting display output to file "{}".'.format(
                    absolute_output_file_path))
                original_stdout = sys.stdout
                output_file = open(absolute_output_file_path, "w")
                sys.stdout = output_file
            else:
                print("")

            datetime_string = self.return_datetime_string(
                self.variables["metadata_datetime"][metadata_type])[:19]

            if metadata_type == "extracted":
                message = 'Metadata extracted (at {} UTC) from file\n{}'.format(
                    datetime_string,
                    self.variables["source_of_metadata"]["extracted"])
            elif ((metadata_type == "prepared") and
                  (self.variables["source_of_metadata"]["prepared"] == 
                   "__input__")):

                message = 'Metadata prepared (at {} UTC) from input.'.format(
                    datetime_string)
            else:
                message = 'Metadata prepared (at {} UTC) from template\n"{}".'.format(
                    datetime_string,
                    self.variables["source_of_metadata"]["prepared"])

            print(message)
            print("")

            if self.options["show_data_types"]["value"]:
                print("Tag value data types are indicated by")
                print("  b - Boolean")
                print("  f - Float")
                print("  i - Integer")
                print("  s - String")
                print("  u - Unknown")
                print("")

            full_tag_names = sorted( self.metadata[metadata_type].keys() )
            if "SourceFile" in full_tag_names:
                full_tag_names.remove("SourceFile")

            maximum_display_tag_name_length = 0
            for full_tag_name in full_tag_names:
                display_tag_name_length = len(full_tag_name)
                if type(self.metadata[metadata_type][full_tag_name]) == list:
                    display_tag_name_length += len("[{}]".format(len(self.metadata[metadata_type][full_tag_name])))
                if display_tag_name_length > maximum_display_tag_name_length:
                    maximum_display_tag_name_length = display_tag_name_length

            self.variables["display_unwrapped_line_format"] = \
                "{} {:<" + str(maximum_display_tag_name_length) + "} {} {}"
            self.variables["display_maximum_length_for_unwrapped_line"] = 80 - maximum_display_tag_name_length

            previous_group_name = ""
            for full_tag_name in full_tag_names:
                if full_tag_name in self.variables["unrecognised_tags"][metadata_type]:
                    recognition_indicator = "\033[1mU\033[0m"
                else:
                    recognition_indicator = " "

                group_name, short_tag_name = full_tag_name.split(":")
                if group_name != previous_group_name:
                    previous_group_name = group_name
                    number_of_leading_dashes = \
                        maximum_display_tag_name_length - len(group_name) - 5
                    display_group_name = "{} {} Group ".format(
                        "-" * number_of_leading_dashes,
                        group_name)
                    print(display_group_name)

                if type(self.metadata[metadata_type][full_tag_name]) == list:
                    list_index = 0
                    while list_index < len(self.metadata[metadata_type][full_tag_name]):
                        self.display_single_element(
                            recognition_indicator,
                            full_tag_name + "[{}]".format(list_index + 1),
                            self.metadata[metadata_type][full_tag_name][list_index])

                        list_index += 1
                else:
                    self.display_single_element(
                        recognition_indicator,
                        full_tag_name,
                        self.metadata[metadata_type][full_tag_name])

            print("")
            if output_file_path != None:
                sys.stdout = original_stdout
                output_file.close()
#
###
#
    def display_single_element(
            self, recognition_indicator, display_tag_name, tag_value):

        data_type = type(tag_value)
        if data_type in self.variables["string_types"]:
            if self.options["show_data_types"]["value"]:
                data_type_indicator = "s"
            else:
                data_type_indicator = " "

            if self.variables["python_version"] == 2:
                encoded_tag_value = tag_value.encode('utf8', 'replace')
            else:
                encoded_tag_value = tag_value

            if (("\n" in tag_value) or 
                (len(tag_value) > self.variables["display_maximum_length_for_unwrapped_line"])):
 
                print(self.variables["display_unwrapped_line_format"].format(
                    recognition_indicator, 
                    display_tag_name, 
                    data_type_indicator, 
                    ""))     
                for line in encoded_tag_value.splitlines():
                    print(self.variables["display_wrapped_line_format"].format(
                        line))
            else:
                print(self.variables["display_unwrapped_line_format"].format(
                    recognition_indicator, 
                    display_tag_name, 
                    data_type_indicator, 
                    tag_value))     

        else:
            if self.options["show_data_types"]["value"]:
                if data_type == int:
                    data_type_indicator = "i"
                elif data_type == float:
                    data_type_indicator = "f"
                elif data_type == bool:
                    data_type_indicator = "b"
                else:
                    data_type_indicator = "u"
            else:
                data_type_indicator = " "

            print(self.variables["display_unwrapped_line_format"].format(
                recognition_indicator, 
                display_tag_name, 
                data_type_indicator, 
                tag_value))     
#
###
#
    def return_formatted_tag_value(self, raw_tag_value):
        function_name = "return_formatted_tag_value"

        if self.variables["prepared_metadata_mode"] == "live":
            format = raw_tag_value
        else:
            format_elements = []
            for text_fragment in self.handlers["string"].parse(raw_tag_value):
                format_elements.append(text_fragment[0])
                if text_fragment[1] != None:
                    format_elements.append("\033[1m{")
                    format_elements.append(text_fragment[1])
                    if text_fragment[2] != "":
                        format_elements.append(":")
                        format_elements.append(text_fragment[2])
                    format_elements.append("}\033[0m")

            format = "".join(format_elements)

        if self.variables["prepared_metadata_mode"] == "test_format":
            prepared_value = format
        else:
            try:
                prepared_value = format.format(
                    **self.variables["substitutions_for_prepared_metadata"])
            except:
                prepared_value = ""
                self.register_a_general_error(
                    function_name, 
                    'Unable to perform substitution(s) for supplied tag name "{}" for template id "{}".'.format(
                        self.variables["source_of_prepared_metadata_value"],
                        self.variables["source_of_metadata"]["prepared"]))

        return prepared_value
#
###
#
    def add_standard_tags_to_prepared_metadata(self):
        function_name = "add_standard_tags_to_prepared_metadata"

        if self.variables["prepared_metadata_mode"] == "live":
            tag_value = self.variables["metadata_datetime_string"]["prepared"]
        else:
            timezone_indicator_option = \
                self.options["timezone_indicator"]["value"]
            datetime_format = \
                "\033[1m{__utcnow__" + \
                self.variables["datetime_format"][timezone_indicator_option][1:] + \
                "\033[0m"

            if self.variables["prepared_metadata_mode"] == "test_format":
                tag_value = datetime_format
            else:
                tag_value = datetime_format.format(
                    **self.variables["substitutions_for_prepared_metadata"])

        for full_tag_name in self.variables["standard_tag_names"]:
            self.metadata["prepared"][full_tag_name] = tag_value
#
###
#
    def prepare_metadata_from_template(
            self, template_id, substitutions={}, mode="live"):

        function_name = "prepare_metadata_from_template"
        self.variables["no_general_error_has_been_registered"] = True

        self.variables["metadata_datetime"]["prepared"] = \
            datetime.datetime.utcnow()
        self.variables["metadata_datetime_string"]["prepared"] = \
            self.return_datetime_string(
                self.variables["metadata_datetime"]["prepared"])
        self.metadata["prepared"] = {}
        self.variables["source_of_metadata"]["prepared"] = template_id
        self.variables["prepared_metadata_mode"] = mode
        self.variables["unrecognised_tags"]["prepared"] = []

        if template_id not in self.variables["templates"]:
            self.register_a_general_error(
                function_name, 
                'Supplied template identifier "{}" is not recognised.'.format(
                    template_id))

        if mode in ["live", "test_format", "test_value"]:
            if mode == "test_format":
                self.variables["substitutions"] = {}
            else:
                self.check_supplied_substitutions(template_id, substitutions)
        else:
            self.register_a_general_error(
                function_name, 
                'Supplied mode "{}" is not recognised. The value may only be "live", "test_format", or "test_value".'.format(mode))

        if self.variables["no_general_error_has_been_registered"]:
            entry_index = 0
            while entry_index < len(self.variables["templates"][template_id]["supplied_tag_name_for_entry"]):

                supplied_tag_name = self.variables["templates"][template_id][
                    "supplied_tag_name_for_entry"][entry_index]
                full_tag_name = self.variables["templates"][template_id][
                    "full_tag_name_for_entry"][entry_index]

                if entry_index in self.variables["templates"][template_id]["entry_indices_of_unrecognised_tags"]:
                    self.variables["unrecognised_tags"]["prepared"].append(
                        full_tag_name)

                if (self.options["add_standard_tags"]["value"] and
                    (full_tag_name in self.variables["standard_tag_names"])):

                    self.register_a_general_error(
                        function_name, 
                        'Tag "{}" may not be used in a template since it will be added automatically to the prepared metadata. Remove the option from template "{}" or change the value of the "add_standard_tags" option to False.'.format(
                            supplied_tag_name, 
                            template_id))

                if supplied_tag_name != "template_id":
                    self.variables["source_of_prepared_metadata_value"] = \
                        supplied_tag_name
                    if type(self.templates[template_id][entry_index][supplied_tag_name]) == list:
                        self.metadata["prepared"][full_tag_name] = []
                        for raw_tag_value in self.templates[template_id][entry_index][supplied_tag_name]:
                            self.metadata["prepared"][full_tag_name].append(
                                self.return_formatted_tag_value(raw_tag_value))
                    else:
                        self.metadata["prepared"][full_tag_name] = \
                            self.return_formatted_tag_value(
                                self.templates[template_id][entry_index][supplied_tag_name])

                entry_index += 1

        if self.variables["no_general_error_has_been_registered"]:
            if self.options["add_standard_tags"]["value"]:
                self.add_standard_tags_to_prepared_metadata()
        else:
            self.metadata["prepared"] = {}
            self.variables["source_of_metadata"]["prepared"] = ""
#
###
#
    def check_supplied_substitutions(self, template_id, substitutions):
        function_name = "check_supplied_substitutions"
        if type(substitutions) != dict:
            self.register_a_general_error(
                function_name, 
                'Supplied subtitutions is not a python dictionary.')

        else:
            for global_substitution_key in self.variables["global_substitution_keys"]:
                if global_substitution_key in substitutions:
                    self.register_a_general_error(
                        function_name, 
                        'The supplied substitutions may not contain the reserved key "{}".'.format(global_substitution_key))

            for required_substitution_key in self.variables["templates"][template_id]["usage_details_for_substitution_key"]:

                if ((required_substitution_key not in substitutions) and
                    (required_substitution_key not in self.variables["global_substitution_keys"])):
                    self.register_a_general_error(
                        function_name, 
                        'No substitution has been supplied for key "{}".'.format(required_substitution_key))

        if self.variables["no_general_error_has_been_registered"]:
            self.variables["substitutions_for_prepared_metadata"] = \
                substitutions.copy()
            self.variables["substitutions_for_prepared_metadata"]["__utcnow__"] = \
                self.variables["metadata_datetime"]["prepared"]
            self.variables["substitutions_for_prepared_metadata"]["__utcnowstr__"] = self.variables["metadata_datetime_string"]["prepared"]
        else:
            self.variables["substitutions_for_prepared_metadata"] = {}
#
###
#
    def prepare_metadata_from_input(self, input_metadata):
        function_name = "prepare_metadata_from_input"
        self.variables["no_general_error_has_been_registered"] = True

        self.variables["metadata_datetime"]["prepared"] = \
            datetime.datetime.utcnow()
        self.variables["metadata_datetime_string"]["prepared"] = \
            self.return_datetime_string(
                self.variables["metadata_datetime"]["prepared"])
        self.metadata["prepared"] = {}
        self.variables["source_of_metadata"]["prepared"] = "__input__"
        self.variables["prepared_metadata_mode"] = "live"
        self.variables["unrecognised_tags"]["prepared"] = []

        if type(input_metadata) != dict:
            self.register_a_general_error(
                function_name, 
                'The supplied input metadata are not in the form of a dictionary.')
        elif len(input_metadata) == 0:
            self.register_a_general_error(
                function_name, 
                'The supplied input metadata contain no entries.')

        if self.variables["no_general_error_has_been_registered"]:
            for supplied_tag_name in input_metadata:
                self.determine_supplied_tag_name_details(supplied_tag_name)
                self.determine_tag_value_details(
                    input_metadata[supplied_tag_name])

                full_tag_name = \
                    self.variables["full_tag_name_for_supplied_tag_name"]

                if not self.variables["supplied_tag_name_is_valid"]:
                    self.register_a_template_error(
                        function_name, 
                        'The supplied tag name "{}" for input metadata is invalid. {}'.format(supplied_tag_name, self.variables["reason_for_supplied_tag_name_invalidity"]))

                if not self.variables["supplied_tag_name_is_recognised"]:
                    self.variables["unrecognised_tags"]["prepared"].append(
                        self.variables["full_tag_name_for_supplied_tag_name"])

                if full_tag_name in self.metadata["prepared"]:
                    self.register_a_template_error(
                        function_name, 
                        'There is a repeat entry for full tag name "{}".'.format(full_tag_name))

                if (self.options["add_standard_tags"]["value"] and
                    (full_tag_name in self.variables["standard_tag_names"])):

                    self.register_a_general_error(
                        function_name, 
                        'Tag "{}" may not be used since it will be added automatically to the prepared metadata. Remove the option from the input or change the value of the "add_standard_tags" option to False.'.format(supplied_tag_name))

                if not self.variables["supplied_tag_value_is_valid"]:
                    self.register_a_template_error(
                        function_name, 
                        'Value for supplied tag name "{}" is not of string type.'.format(supplied_tag_name))

                if (self.variables["tag_value_contains_multiple_values"] and 
                    (not self.variables["supplied_tag_name_supports_multiple_values"])):
                    self.register_a_template_error(
                        function_name, 
                        'Tag "{}" does not support multiple values.'.format(
                            supplied_tag_name))

                self.metadata["prepared"][full_tag_name] = \
                    input_metadata[supplied_tag_name]

        if self.variables["no_general_error_has_been_registered"]:
            if self.options["add_standard_tags"]["value"]:
                self.add_standard_tags_to_prepared_metadata()
        else:
            self.metadata["prepared"] = {}
            self.variables["source_of_metadata"]["prepared"] = ""
#
###
#
    def extract(self, source_file_path, should_return_metadata=True):
        function_name = "extract"
        self.variables["no_general_error_has_been_registered"] = True

        if not type(source_file_path) in self.variables["string_types"]:
            self.register_a_general_error(
                function_name, 
                'Supplied source file path was not of a string type.'.format(
                    self.variables["source_of_metadata"]["extracted"]))
        else:
            if source_file_path.startswith("~"):
                self.variables["source_of_metadata"]["extracted"] = \
                    os.path.expanduser(source_file_path)
            else:
                self.variables["source_of_metadata"]["extracted"] = \
                    os.path.abspath(source_file_path)
            self.metadata["extracted"] = {}
            self.variables["metadata_datetime"]["extracted"] = \
                datetime.datetime.utcnow()
            self.variables["metadata_datetime_string"]["extracted"] = \
                self.return_datetime_string(
                    self.variables["metadata_datetime"]["extracted"])

            if not os.path.isfile(self.variables["source_of_metadata"]["extracted"]):
                self.register_a_general_error(
                    function_name, 
                    'Supplied file path "{}" is invalid.'.format(
                        self.variables["source_of_metadata"]["extracted"]))

        if self.variables["no_general_error_has_been_registered"]:
            file_path_for_os = self.return_file_path_for_os(
                self.variables["source_of_metadata"]["extracted"])
            gps_extraction_option = \
                self.options["gps_extraction"]["value"]
            exiftool_arguments = \
                self.variables["standard_exiftool_extraction_arguments"] + \
                [self.variables["gps_extraction_formats"][gps_extraction_option],
                 file_path_for_os]
            try:
                exiftool_return_string = \
                    subprocess.check_output(exiftool_arguments)
            except:
                self.register_a_general_error(
                    function_name, 
                    "ExifTool extraction command failed. The selected file was probably of a type that does not support embedded metadata.")
            else:
                try:
                    self.metadata["extracted"] = yaml.load(
                        exiftool_return_string, 
                        Loader=yaml.SafeLoader)[0]
                except:
                    self.register_a_general_error(
                        function_name, 
                        "Return from ExifTool extraction command could not be parsed.")

        if not self.variables["no_general_error_has_been_registered"]:
            self.variables["source_of_metadata"]["extracted"] = ""
            self.metadata["extracted"] = {}

        if should_return_metadata:
            return self.metadata["extracted"]
#
###
#
    def check_if_tags_would_be_overwritten(self, mode):
        function_name = "check_if_tags_would_be_overwritten"

        if mode == "test":
            verbosity_level = 3
        else:
            verbosity_level = self.options["verbosity_level"]["value"]

        tags_to_be_overwritten = []
        maximum_number_of_sub_values = 0
        prepared_tag_names = sorted(self.metadata["prepared"])
        for prepared_tag_name in prepared_tag_names:
            if prepared_tag_name in self.metadata["extracted"]:
                tags_to_be_overwritten.append(prepared_tag_name)
                if type(self.metadata["prepared"][prepared_tag_name]) == list:
                    number_of_sub_values = \
                        len(self.metadata["prepared"][prepared_tag_name])
                    if number_of_sub_values > maximum_number_of_sub_values:
                        maximum_number_of_sub_values = number_of_sub_values

                if type(self.metadata["extracted"][prepared_tag_name]) == list:
                    number_of_sub_values = \
                        len(self.metadata["extracted"][prepared_tag_name])
                    if number_of_sub_values > maximum_number_of_sub_values:
                        maximum_number_of_sub_values = number_of_sub_values

            maximum_display_tag_name_length = 9
            if maximum_number_of_sub_values > 0:
                maximum_display_tag_name_length += \
                    len("[{}]".format(maximum_number_of_sub_values))

            self.variables["display_unwrapped_line_format"] = \
                "{} {:<" + str(maximum_display_tag_name_length) + "} {} {}"
            self.variables["display_maximum_length_for_unwrapped_line"] = \
                80 - maximum_display_tag_name_length

        number_of_tags_to_be_overwritten = len(tags_to_be_overwritten)
        if number_of_tags_to_be_overwritten == 0:
            if mode == "test":
                print("\nNo tags will be overwritten in the target file.\n")
        else:
            self.show_a_warning_message(
                function_name, 
                'The prepared metadata will overwrite {} tags in file "{}".'.format(
                    number_of_tags_to_be_overwritten,
                    self.variables["source_of_metadata"]["extracted"]))

            if verbosity_level > 1:
                recognition_indicator = " "
                for tag_name in tags_to_be_overwritten:
                    print(tag_name)
                    if verbosity_level > 2:
                        if type(self.metadata["extracted"][tag_name]) == list:
                            list_number = 1
                            for sub_value in self.metadata["extracted"][tag_name]:
                                self.display_single_element(
                                    recognition_indicator,
                                    "Extracted[{}]".format(list_number),
                                    sub_value)
                                list_number += 1
                        else:
                            self.display_single_element(
                                recognition_indicator,
                                "Extracted",
                                self.metadata["extracted"][tag_name])

                        if type(self.metadata["prepared"][tag_name]) == list:
                            list_number = 1
                            for sub_value in self.metadata["prepared"][tag_name]:
                                self.display_single_element(
                                    recognition_indicator,
                                    "Prepared[{}]".format(list_number),
                                    sub_value)
                                list_number += 1
                        else:
                            self.display_single_element(
                                recognition_indicator,
                                "Prepared",
                                self.metadata["prepared"][tag_name])

        if number_of_tags_to_be_overwritten == 0:
            return False
        else:
            return True
#
###
#
    def embed_prepared_metadata(self):
        function_name = "embed_prepared_metadata"
        self.variables["no_general_error_has_been_registered"] = True

        if self.metadata["extracted"] == {}:
            self.register_a_general_error(
                function_name, 
                "No target file has been selected.")

        if self.metadata["prepared"] == {}:
            self.register_a_general_error(
                function_name, 
                "Prepared metadata have not been created.")

        if self.variables["no_general_error_has_been_registered"]:
            exiftool_arguments = ["exiftool", "-overwrite_original"]
            tag_names = sorted( self.metadata["prepared"].keys() )
            for full_tag_name in tag_names:
                if full_tag_name.startswith("UNKNOWN"):
                    applied_tag_name = full_tag_name[8:]
                else:
                    applied_tag_name = full_tag_name

                value_type = type(self.metadata["prepared"][full_tag_name])

                if value_type == list:
                    for value in self.metadata["prepared"][full_tag_name]:
                        if self.variables["python_version"] == 2:
                            exiftool_arguments.append("-{}={}".format(
                                applied_tag_name, 
                                value.encode('utf8', 'replace'))),
                        else:
                            exiftool_arguments.append("-{}={}".format(
                                applied_tag_name,
                                value))

                elif self.variables["python_version"] == 2:
                    exiftool_arguments.append("-{}={}".format(
                        applied_tag_name, 
                        self.metadata["prepared"][full_tag_name].encode('utf8', 'replace')))
                else:
                    exiftool_arguments.append("-{}={}".format(
                        applied_tag_name, 
                        self.metadata["prepared"][full_tag_name]))

            file_path_for_os = self.return_file_path_for_os(
                self.variables["source_of_metadata"]["extracted"])
            exiftool_arguments.append(file_path_for_os)
            exit_code = subprocess.call(exiftool_arguments)
            if exit_code != 0:
                self.register_a_general_error(
                    function_name, 
                    "ExifTool returned an error whilst trying to embed metadata.")

        if self.variables["no_general_error_has_been_registered"]:
            self.variables["source_of_metadata"]["extracted"] = ""
            self.metadata["extracted"] = {}
            return 0
        else:
            return 1
#
###
#
    def embed_from_template(self, template_id, substitutions, file_path):
        function_name = "embed_from_template"
        self.variables["no_general_error_has_been_registered"] = True

        exit_code = 1
        self.prepare_metadata_from_template(template_id, substitutions)
        if self.metadata["prepared"] != {}:
            number_of_unrecognised_tags = \
                len(self.variables["unrecognised_tags"]["prepared"])
            if number_of_unrecognised_tags > 0:
                if self.options["allow_unrecognised_tags"]["value"]:
                    self.show_a_warning_message(
                        function_name,
                        'The template contains {} unrecognised tag names. There is no guarantee that these represent valid metadata fields.'.format(
                            number_of_unrecognised_tags))
                else:
                    self.register_a_general_error(
                        function_name,
                        'The template contains {} unrecognised tag names. Add appropriate details to the accompany file "module_exiftool_recognised_tags.dat" in order to avoid this problem.'.format(
                            number_of_unrecognised_tags))

        if self.variables["no_general_error_has_been_registered"]:
            self.extract(file_path, False)
            if self.metadata["extracted"] != {}:
                tags_would_be_overwritten = \
                    self.check_if_tags_would_be_overwritten("live")
                if tags_would_be_overwritten and not self.options["allow_tag_overwrites"]["value"]:
                    self.register_a_general_error(
                        function_name, 
                        'Tag overwrites are not allowed. Change the value of the "allow_tag_overwrites" option to True in order to continue.')
                else:
                    exit_code = self.embed_prepared_metadata()

        if exit_code == 0:
            return 0
        else:
            return 1
#
###
#
    def embed_from_input(self, input_metadata, file_path):
        function_name = "embed_from_input"
        self.variables["no_general_error_has_been_registered"] = True

        exit_code = 1
        self.prepare_metadata_from_input(input_metadata)
        if self.metadata["prepared"] != {}:
            number_of_unrecognised_tags = \
                len(self.variables["unrecognised_tags"]["prepared"])
            if number_of_unrecognised_tags > 0:
                if self.options["allow_unrecognised_tags"]["value"]:
                    self.show_a_warning_message(
                        function_name,
                        'The input metadata contain {} unrecognised tag names. There is no guarantee that these represent valid metadata fields.'.format(
                            number_of_unrecognised_tags))
                else:
                    self.register_a_general_error(
                        function_name,
                        'The input metadata contain {} unrecognised tag names. Add appropriate details to the accompany file "module_exiftool_recognised_tags.dat" in order to avoid this problem.'.format(
                            number_of_unrecognised_tags))

        if self.variables["no_general_error_has_been_registered"]:
            self.extract(file_path, False)
            if self.metadata["extracted"] != {}:
                tags_would_be_overwritten = \
                    self.check_if_tags_would_be_overwritten("live")
                if tags_would_be_overwritten and not self.options["allow_tag_overwrites"]["value"]:
                    self.register_a_general_error(
                        function_name, 
                        'Tag overwrites are not allowed. Change the value of the "allow_tag_overwrites" option to True in order to continue.')
                else:
                    exit_code = self.embed_prepared_metadata()

        if exit_code == 0:
            return 0
        else:
            return 1
#
###
#
    def test_from_template(
            self, template_id, substitutions=None, file_path=None):

        function_name = "test_from_template"

        if substitutions == None:
            self.prepare_metadata_from_template(
                template_id, {}, "test_format")
        else:
            self.prepare_metadata_from_template(
                template_id, substitutions, "test_value")

        if self.metadata["prepared"] != {}:
            self.display("prepared")

            number_of_unrecognised_tags = \
                len(self.variables["unrecognised_tags"]["prepared"])
            if number_of_unrecognised_tags > 0:
                if self.options["allow_unrecognised_tags"]["value"]:
                    self.show_a_warning_message(
                        function_name,
                        'The template contains {} unrecognised tag names, which are indicated by a "U" in the first column of the listing above. There is no guarantee that these represent valid metadata fields.'.format(
                            number_of_unrecognised_tags))
                else:
                    self.register_a_general_error(
                        function_name,
                        'The template contains {} unrecognised tag names, which are indicated by a "U" in the first column of the listing above. Add appropriate details to the accompany file "module_exiftool_recognised_tags.dat" in order to avoid this problem.'.format(
                            number_of_unrecognised_tags))

                print("")

            if file_path != None:
                self.extract(file_path, False)
                if self.metadata["extracted"] != {}:
                    tags_would_be_overwritten = \
                        self.check_if_tags_would_be_overwritten("test")
                    if tags_would_be_overwritten and not self.options["allow_tag_overwrites"]["value"]:
                        self.register_a_general_error(
                            function_name, 
                            'Tag overwrites are not allowed. Change the value of the "allow_tag_overwrites" option to True in order to continue.')                              
#
###
#
    def test_from_input(self, input_metadata, file_path=None):
        function_name = "test_from_input"

        self.prepare_metadata_from_input(input_metadata)
        if self.metadata["prepared"] != {}:
            self.display("prepared")

            number_of_unrecognised_tags = \
                len(self.variables["unrecognised_tags"]["prepared"])
            if number_of_unrecognised_tags > 0:
                if self.options["allow_unrecognised_tags"]["value"]:
                    self.show_a_warning_message(
                        function_name,
                        'The input contains {} unrecognised tag names, which are indicated by a "U" in the first column of the listing above. There is no guarantee that these represent valid metadata fields.'.format(
                            number_of_unrecognised_tags))
                else:
                    self.register_a_general_error(
                        function_name,
                        'The input contains {} unrecognised tag names, which are indicated by a "U" in the first column of the listing above. Add appropriate details to the accompany file "module_exiftool_recognised_tags.dat" in order to avoid this problem.'.format(
                            number_of_unrecognised_tags))

                print("")

            if file_path != None:
                self.extract(file_path, False)
                if self.metadata["extracted"] != {}:
                    tags_would_be_overwritten = \
                        self.check_if_tags_would_be_overwritten("test")
                    if tags_would_be_overwritten and not self.options["allow_tag_overwrites"]["value"]:
                        self.register_a_general_error(
                            function_name, 
                            'Tag overwrites are not allowed. Change the value of the "allow_tag_overwrites" option to True in order to continue.')
