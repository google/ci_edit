
# Glossary of terms used in the program source.

Note: this information is not useful for *using* the editor. It's intended for
those working on (programming) the editor itself.

child
- a window
- reference to a window contained by this window
- a parent may have 0..* children
- property of parent

contractor (? I'm still considering this term)
- a window
- doing work on or for a host
- a host will have 0..1 contractor
- property of host

controller
- a controller
- keybindings
- a controller will have 1..1 view
- property of view

host
- a window
- the view requesting work
- likely the parent, but not necessarily the parent
- a contractor will have 0..1 host
- property of contractor

parent
- a window
- The window holding this window
- The given window is a child of the parent
- a child will have 1..1 parent (the top parent is the program instance)
- property of child

view
- a window
- the window for a given controller
- controller and view are 1:1
- a view will have 1..1 model (an empty model will be created for the view if
    necessary)
- property of a controller
- property of a model

model
- a text buffer
- a mutator
- a model will have 0..* views
