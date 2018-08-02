import unittest
from irtools.kits.json_structure import JsonStructure


class TestJsonStructure(unittest.TestCase):

    def test_with_required(self):
        class JSTestRequired(JsonStructure):
            _js_required_structure = {
                'root': {
                    'abc': str,
                    'xyzint': int,
                    'xyzfloat': float,
                    'list_of_string': [str],
                    'list_of_dict': [dict],
                    'list_js_or_dict': [JsonStructure, dict],
                    'inner': {
                        'js': JsonStructure,
                        'abc': str,
                        'inner_list': [str, dict, list, JsonStructure]
                    }
                }
            }

        JSTestRequired(
            json_data={
                'abc': 'random string',
                'xyzint': 123,
                'xyzfloat': 10.10,
                'list_of_string': ['a', 'b', 'c'],
                'list_of_dict': [{}],
                'list_js_or_dict': [JsonStructure(), {}],
                'inner': {
                    'js': JsonStructure(),
                    'abc': 'another string',
                    'inner_list': ['abc', {}, [], JsonStructure()]
                }
            }
        )

        self.assertTrue(True)

    def test_with_default(self):
        class JSTestDefault(JsonStructure):
            _js_default_data = {
                'root': {
                    'abc': 'random string',
                    'xyzint': 123,
                    'xyzfloat': 10.10,
                    'list_of_string': ['a', 'b', 'c'],
                    'list_of_dict': [{}],
                    'list_js_or_dict': [JsonStructure(), {}],
                    'inner': {
                        'js': JsonStructure(),
                        'abc': 'another string',
                        'inner_list': ['abc', {}, [], JsonStructure()]
                    }
                }
            }

        JSTestDefault(
            json_data={
                'abc': 'my string',
                'xyzint': 765,
                'xyzfloat': 10.10,
                'list_of_string': ['a', 'x'],
                'list_of_dict': [{'a': 1}],
                'list_js_or_dict': [{}],
                'inner': {
                    'abc': 'a string',
                    'inner_list': ['abc']
                }
            }
        )

        self.assertTrue(True)

    def test_with_required_and_default(self):
        class JSTestDefault2(JsonStructure):
            _js_default_data = {
                'root': {
                    'abc': 'random string',
                    'xyzint': 123,
                    'xyzfloat': 10.10,
                    'list_of_string': ['a', 'b', 'c'],
                    'list_of_dict': [{}],
                    'list_js_or_dict': [JsonStructure(), {}],
                    'inner': {
                        'js': JsonStructure(),
                        'abc': 'another string',
                        'inner_list': ['abc', {}, [], JsonStructure()]
                    }
                }
            }

        class JSTestReqDef(JsonStructure):
            _js_required_structure = {
                'root': {
                    'abc': str,
                    'xyzint': int,
                    'xyzfloat': float,
                    'list_of_string': [str],
                    'list_of_dict': [dict],
                    'list_js_or_dict': [JsonStructure, dict],
                    'inner': {
                        'js': JSTestDefault2,
                        'abc': str,
                        'inner_list': [str, dict, list]
                    }
                }
            }
            _js_default_data = {
                'root': {
                    'list_of_string': ['a', 'b', 'c'],
                    'list_of_dict': [{}],
                    'list_js_or_dict': [JsonStructure(), {}],
                    'inner': {
                        'js': JSTestDefault2(),
                        'abc': 'another string',
                        'inner_list': ['abc', {}, []]
                    }
                }
            }

        JSTestReqDef(
            json_data={
                'abc': 'my string',
                'xyzint': 765,
                'xyzfloat': 10.10,
                'inner': {
                    'js': JSTestDefault2(json_data={'something else': 123}),
                    'inner_list': ['abc']
                }
            }
        )

        self.assertTrue(True)

    def test_load_convert(self):
        class JSInner(JsonStructure):
            _js_required_structure = {
                'root': {
                    'a': int,
                }
            }
            _js_default_data = {
                'root': {
                    'b': 'hello'
                }
            }

        class JSOuter(JsonStructure):
            _js_required_structure = {
                'root': {
                    'js': JSInner,
                    'meta': {'label': str},
                    'js_list': [JSInner],
                }
            }

        o = JSOuter(
            json_data={
                'js': {'a': 1},
                'meta': {'label': '123'},
                'js_list': [{'a': 2}, {'a': 3}],
            }
        )
        self.assertDictEqual(o.js.export_to_json_data(), {'a': 1, 'b': 'hello'})
        self.assertTrue(isinstance(o.js, JSInner))
        self.assertTrue(all(isinstance(js, JSInner) for js in o.js_list))
