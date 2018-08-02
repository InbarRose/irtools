#  Standard Imports
import json
import types

# irtools Imports
from irtools import *

log = logging.getLogger('irtools.kits.json_structure')


class JsonStructureException(Exception):
    pass


class LoadJsonDataError(JsonStructureException):
    pass


class PropertyGetError(JsonStructureException):
    pass


class PropertyPathError(JsonStructureException):
    pass


class MissingKeyError(LoadJsonDataError):
    pass


class WrongTypeError(LoadJsonDataError):
    pass


class JsonStructure(object):
    """
    a class which wraps a json object,
    essentially making it easy to save and load objects whose underlying structure is json.
    such as when communicating with a restful API that returns JSON structured objects.

    This class is intended to be extended with features specific to your objects
    This class can and should be embedded any arbitrary times into itself
    meaning that sub objects that require special functions could be their own JsonStructure, although not required
    """
    # to build a required structure,
    # build a mock of the json object structure, will check key values against types
    # starts from root, to specify that the root of a JsonStructure should always be a dictionary
    # anything beyond the required structure is not checked, so only put structure you must enforce here or leave blank
    # if a lists is placed in the required structure then we treat it specially
    # we simply check that every item provided is of one of those types (or an instance of class)
    _js_required_structure = {
        'root': {}
    }

    # to add default data to the structure,
    # specify using a mock of the json object structure, will load the values by keys as defaults if not provided
    # you do not need to provide any default data, if their is a key then it's value will be set as default,
    # default values do not need to be specified if there are any required structures or visa versa,
    # however, any missing required data will result in an LoadJsonDataError exception
    # and all default values will be added to the structure unless real values are provided instead
    _js_default_data = {
        'root': {}
    }

    # to add easily accessible properties to your object
    # using the properties will let you define a custom key that will be used to access values in your object
    # for example:
    # property: {'id': ['object-id']}
    #   means accessing js.id or js['id'] you will get the 'object-id' from data.
    # property: {'embedded': ['deeply', 'embedded', 'value']}
    #   means accessing js.embedded or js['embedded'] you will get the 'value' from data['deeply']['embedded'].
    # using properties will let you access keys in child members as well, recursively calling .get on the inner objects
    # a property is a dictionary mapping the property key to a list which is the path of .get to get to the value
    _js_properties = {

    }

    # == class flags ==
    # load_convert - for when a subclass of JsonStructure is specified in the required structure
    # if the loaded item is not of the type (which makes sense when reading from raw json) then we try to convert
    # this only happens when the item is a dictionary object.
    # we attempt to convert using required_class(json_data=item)
    # we expect that the required_class will handle its own load validation
    _flag_load_convert = True

    def __init__(self, json_data=None):
        # members
        self.__json_data = {}
        self.load_data(json_data)

    def _add_defaults_to_data(self, json_data=None):
        """
        add default data to the json_data before loading the data
        :param json_data:
        :return:
        """
        if json_data is None:
            # if we didn't get any data, set it to an empty dictionary so we can add defaults
            json_data = {}
        # recursively add default values to the structure
        json_data = self.__recurse_add_defaults(json_data, self._js_default_data['root'])
        return json_data

    def __recurse_add_defaults(self, json_data_at_key, defaults_at_key):
        """
        recursively goes through all default data and creates the default values in the json_data if they don't exist
        :param json_data_at_key:
        :param defaults_at_key:
        :return:
        """
        # loop over all the keys in this layer of the defaults
        for inner_key, default_value in defaults_at_key.items():
            # we should only enter one of these conditions
            # noinspection PyTypeChecker
            if isinstance(default_value, dict):
                # value is a dictionary, set to a dictionary
                json_data_at_key.setdefault(inner_key, {})
                if default_value.keys():
                    # recurse down because this dictionary has keys
                    self.__recurse_add_defaults(json_data_at_key[inner_key], defaults_at_key[inner_key])
            elif isinstance(default_value, list):
                # value is a list, set to a list
                json_data_at_key.setdefault(inner_key, [])
                if len(default_value):
                    self.__recurse_add_defaults_list(json_data_at_key[inner_key], defaults_at_key[inner_key])
            # noinspection PyTypeChecker
            elif isinstance(default_value, (types.ClassType, type)) and issubclass(default_value, JsonStructure):
                # value is a JsonStructure class, initialize a new one
                json_data_at_key.setdefault(inner_key, default_value())
            else:
                # if it is any other type of value we simply set it.
                # this should be a string or a number of some kind, but we won't be too strict
                json_data_at_key.setdefault(inner_key, default_value)
        # returns the json_data
        return json_data_at_key

    def __recurse_add_defaults_list(self, json_data_list, defaults_list):
        for index, item in enumerate(defaults_list):
            if index < len(json_data_list):
                if isinstance(item, dict) and isinstance(json_data_list[index], dict):
                    self.__recurse_add_defaults(json_data_list[index], item)
                elif isinstance(item, list) and isinstance(json_data_list[index], list):
                    self.__recurse_add_defaults_list(json_data_list[index], item)
            elif isinstance(item, dict):
                json_data_list.append(self.__recurse_add_defaults({}, item))
            elif isinstance(item, list):
                json_data_list.append(self.__recurse_add_defaults_list([], item))
            elif isinstance(item, JsonStructure):
                json_data_list.append(item.export_to_json_data())
            else:
                json_data_list.append(item)
        return json_data_list

    def load_data(self, json_data):
        """load a json_object into this JsonStructure"""
        try:
            self._load_data(json_data)
        except Exception as exc:
            log.error('error loading data: exc={} self={} data={}'.format(exc, repr(self), json_data))
            raise

    def _load_data(self, json_data):
        """
        internal function for loading data,
        performs default data addition a required check on the data and then sets the json data
        :param json_data:
        :return:
        """
        # add any default data specified
        json_data = self._add_defaults_to_data(json_data)
        # check required data
        self.__recurse_check_required(json_data, self._js_required_structure['root'])
        # load the data
        self._hook_set_json_data(json_data)

    def __recurse_check_required(self, json_data_at_key, required_at_key, path=''):
        """
        recursively goes through all required data and verifies the json data matches
        :param json_data_at_key:
        :param required_at_key:
        :param path: for debugging location of exceptions
        :return:
        """
        # loop over all the keys in this layer of the required
        for inner_key, required_type_object in required_at_key.items():
            in_path = '.'.join(filter(None, [path, inner_key]))
            # make sure required key exists
            if inner_key not in json_data_at_key:
                raise MissingKeyError(inner_key, path)
            #  see if we can convert the data to the required type if it isn't already
            if self.__check_load_convert(required_type_object, json_data_at_key[inner_key]):
                json_data_at_key[inner_key] = self.__load_convert(
                    convert_data=json_data_at_key[inner_key],
                    convert_class=required_type_object,
                    path=in_path,
                )
            # make sure required type matches or is instance of required class
            if not self.__check_required_type_match(json_data_at_key[inner_key], required_type_object):
                raise WrongTypeError(required_type_object, in_path)
            # now perform the recursive and list part
            # we should only enter one of these conditions
            if isinstance(required_type_object, dict) and required_type_object.keys():
                # recurse down because this dictionary has keys
                self.__recurse_check_required(
                    json_data_at_key[inner_key],
                    required_at_key[inner_key],
                    path=in_path)
            elif isinstance(required_type_object, list) and len(required_type_object):
                # check if we can convert the list of json_data into the required type
                # this will only happen if there is only 1 type specified in the list
                # (ie: we requires a list to be of json_structure items)
                # and we check that we can load/convert all the items
                if len(required_type_object) == 1 and all(
                        self.__check_load_convert(required_type_object[0], d) for d in json_data_at_key[inner_key]):
                    # we are going to convert the whole list before validating
                    json_data_at_key[inner_key] = [self.__load_convert(
                        convert_data=d,
                        convert_class=required_type_object[0],
                        path=in_path,
                    ) for d in json_data_at_key[inner_key]]
                # recurse down because this list has items in it
                self.__check_required_list(
                    json_data_at_key[inner_key],
                    required_at_key[inner_key],
                    path=in_path)
        # returns the json_data
        return json_data_at_key

    def __load_convert(self, convert_data, convert_class, path):
        """converts data during loading to required class type"""
        try:
            return convert_class(json_data=convert_data)
        except Exception as exc:
            log.error('Exception trying to convert data on load: exc={} convert_class={} path={}'.format(
                exc, convert_class, path))
            return convert_data

    def __check_load_convert(self, required_type_object, candidate_data):
        """checks if we can convert the data to required class type during loading"""
        if not self._flag_load_convert:
            # if the flag is off, we should not perform conversions
            return False
        if not isinstance(candidate_data, dict):
            # if the data is not a dictionary, we do not need to convert anything
            return False
        if isinstance(required_type_object, (types.ClassType, type)) \
                and not issubclass(required_type_object, JsonStructure):
            # if the required type is not a subclass of JsonStructure then we will not convert it
            return False
        return True

    def __check_required_list(self, json_data_list, required_list, path=''):
        """
        iterates over a list of provided data and checks it against a list of required types
        :param json_data_list:
        :param required_list:
        :param path:
        :return:
        """
        for index, item in enumerate(json_data_list):
            for required_type_object in required_list:
                if self.__check_required_type_match(item, required_type_object):
                    break
            else:
                raise WrongTypeError(item, required_list, path, index)

    def __check_required_type_match(self, check_value, required_type_object):
        if isinstance(required_type_object, (types.ClassType, type)):
            # noinspection PyTypeChecker
            if not isinstance(check_value, required_type_object):
                return False
        elif isinstance(required_type_object, (list, dict)):
            # todo: abstract to all collection types and maybe other types as well
            if not isinstance(check_value, type(required_type_object)):
                return False
        else:
            if not isinstance(check_value, required_type_object):
                return False
        return True

    def _hook_set_json_data(self, json_data):
        """a function to provide easy extendability to setting the json data"""
        self.__json_data = json_data

    def _hook_set_json_key(self, key, value):
        """a function to provide easy extendability to setting a json key"""
        self.__json_data[key] = value

    def _hook_get_json_key(self, key):
        """a function to provide easy extendability to getting a json key"""
        if key in self._js_properties:
            return self._hook_get_property(key)
        return self.__json_data[key]

    def _hook_get_property(self, key, default=None):
        """a function to provide easy extendability to getting a property"""
        property_path = self._js_properties[key]
        if not isinstance(property_path, list):
            raise PropertyPathError(key, property_path)
        try:
            value = reduce(lambda obj, k: obj.get(k), property_path, self)
        except Exception as exc:
            if isinstance(exc, AttributeError):
                if exc.message.endswith("instance has no attribute 'get'"):
                    raise PropertyGetError(key, exc.message.split()[0])
            elif isinstance(exc, KeyError):
                return default
            raise
        else:
            return value

    def export_to_json_string(self, **kwargs):
        """
        exports the data to a json string using json.dumps
        :return:
        """
        use_default_settings = kwargs.pop('use_default_settings', True)
        if use_default_settings:
            # makes it easier to debug issues
            kwargs.setdefault('sort_keys', True)
        return json.dumps(self.export_to_json_data(), **kwargs)

    def export_to_json_data(self):
        """
        formats all json_data in this JsonStructure as a json serializable object (dict)
        :return: json serializable object (dict)
        """
        export_json_data = {}
        export_json_data = self.__recurse_export_data(export_json_data, self.__json_data)
        return export_json_data

    def __recurse_export_data(self, export_json_data_at_key, internal_json_data_at_key):
        """
        recursively goes through all the json data and makes sure to convert it all to json serializable objects
        :param export_json_data_at_key:
        :param internal_json_data_at_key:
        :return:
        """
        # loop over all the keys in this layer of the internal json data
        for inner_key, inner_value in internal_json_data_at_key.items():
            # we should only enter one of these conditions
            if isinstance(inner_value, dict):
                self.__recurse_export_data(
                    export_json_data_at_key.setdefault(inner_key, {}),
                    inner_value)
            elif isinstance(inner_value, list):
                self.__recurse_export_data_list(
                    export_json_data_at_key.setdefault(inner_key, []),
                    inner_value)
            elif isinstance(inner_value, JsonStructure):
                # value is a JsonStructure instance, call it's export_to_json_data method
                export_json_data_at_key.setdefault(inner_key, inner_value.export_to_json_data())
            else:
                # if it is any other type of value we simply set it.
                # this should be a string or a number of some kind, but we won't be too strict
                export_json_data_at_key.setdefault(inner_key, inner_value)
        # returns the json_data
        return export_json_data_at_key

    def __recurse_export_data_list(self, export_list, values_list):
        """
        iterates over a list to be exported and makes sure to call required recursive exports if needed
        :param export_list:
        :param values_list:
        :return:
        """
        for item in values_list:
            if isinstance(item, dict):
                export_list.append(self.__recurse_export_data({}, item))
            elif isinstance(item, list):
                export_list.append(self.__recurse_export_data_list([], item))
            elif isinstance(item, JsonStructure):
                export_list.append(item.export_to_json_data())
            else:
                export_list.append(item)

    def get(self, key, default=None, raise_on_missing=False):
        try:
            return self._hook_get_json_key(key)
        except KeyError:
            if raise_on_missing:
                raise
            return default

    def __len__(self):
        return len(self.__json_data)

    def __eq__(self, other):
        if isinstance(other, JsonStructure):
            return bool(self.export_to_json_data() == other.export_to_json_data())
        else:
            return super(JsonStructure, self).__eq__(other)

    def _repr_name(self):
        return self.__class__.__name__

    def _repr_head(self):
        return []

    def _repr_body(self):
        return self.export_to_json_data()

    def __repr__(self):
        return '<{}({}): {}>'.format(self._repr_name(), ' '.join(self._repr_head()), self._repr_body())

    def get_fields(self):
        """get a list of the keys that are "real" fields of this object's underlying json"""
        return sorted(self.__json_data.keys())

    def get_properties(self):
        """get a list of the keys that are "property" fields of this object"""
        return sorted(self._js_properties.keys())

    def __dir__(self):
        object_directory = dir(self.__class__)
        object_directory.extend(self.get_fields())
        object_directory.extend(self.get_properties())
        return object_directory

    def __getitem__(self, item):
        """provides easy access to this object by allowing js[item] access to data members or properties"""
        return self._hook_get_json_key(item)

    def __getattr__(self, item):
        """provides easy access to this object by allowing js.item access to data members or properties"""
        # note, that we do not provide the opposite action such as we do with __getitem__ and __setitem__
        # mostly because properties make this a very difficult situation - maybe in the future
        return self._hook_get_json_key(item)

    def __setitem__(self, key, value):
        """provides easy access to this object by allowing js[item] = value setting to data members or properties"""
        self._hook_set_json_key(key, value)

    def __nonzero__(self):
        return True
