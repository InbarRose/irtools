# csv utils make reading and writing csv files easy.

## sample CSV file


a|b|c
---|---|---
1|hello|value1
2|goodbye|value2
3|bon apetite|value3

### to read the sample csv file
```
>>> rowdicts = utils.read_csv('/path/to/sample.csv')
>>> rowdicts
[{u'a': u'1', u'c': u'value1', u'b': u'hello'}, {u'a': u'2', u'c': u'value2', u'b': u'goodbye'}, {u'a': u'3', u'c': u'value3', u'b': u'bon apetite'}]
```

### to write the sample csv file
```
>>> rowdicts = [{u'a': u'1', u'c': u'value1', u'b': u'hello'}, {u'a': u'2', u'c': u'value2', u'b': u'goodbye'}, {u'a': u'3', u'c': u'value3', u'b': u'bon apetite'}]
>>> utils.write_csv('/path/to/sample.csv', rowdicts)
```
