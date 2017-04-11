
# Python comment
/* Not a comment */
/** Not a comment */
<!-- Not a coment -->
// Not a comment
<script> Still Python (no embeded script) </script>

# TODO(dschuyler): A test comment.

'a\\' # double escape
'a\\\\' # quadruple escape
'a\02112s\0a\01b\012cfd23323sa' # numbers
'\nfiller\w\\aaa\adf\bfsdf\'d\\\'sdff' # special values

"a\\" # double escape
"a\\\\" # quadruple escape
"filler\nsfas\w\\aaa\adf\bfsdf\"d\\\"sadff" # special values

'''asd\nsad'a"fsadf''' # triple single quotes
r'''asd\nsad'a"fsadf''' # triple single quotes

"""asd\nsad'a"fsadf""" # triple double quotes
r"""asd\nsad'a"fsadf""" # triple double quotes

class Foo:
  def __init__(self, data):
    print data

  def blah(self):
    pass

