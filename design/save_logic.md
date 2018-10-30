
Note: these are outline notes I used to work through design issues. They
probably don't make a lot of sense to another reader at the moment. My
apologies.


def is_safe_to_write
    t) write
    f) confirm_overwrite
        y) write
        n) switch_to_host

ui_quit
    is_dirty
        t) message: this file is not saved, please save or close it.
           switch_to_host
        f) has_unsaved
            t) switch_to_unsaved,
               message: this file is not saved, please save or close it.
               switch_to_host
            f) quit_now

too complicated:     ui_quit
    is_dirty
        t) confirm_save
            y) is_safe_to_write
                t) write
                f) confirm_overwrite
                    y) write,
                       has_unsaved
                    n) switch_to_host (cancel the quit)
            n) close_buffer_now,
               has_unsaved
            c) switch_to_host (cancel the quit)
        f) has_unsaved
            t) switch_to_unsaved,
               is_dirty
            f) quit_now
                f) confirm_overwrite
                    y) write,
                       has_unsaved
                    n) switch_to_host (cancel the quit)

ui_save
    is_dirty
        t) is_safe_to_write
        f) switch_to_host

ui_save_as
    cr) is_safe_to_write
    esc) switch_to_host
