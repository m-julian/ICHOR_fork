import os
import sys
from typing import Callable, List, Tuple
from uuid import uuid4

from ichor.problem_finder import ProblemFinder
from ichor.tab_completer import ListCompleter


class Menu(object):
    """A constructor class that makes menus for menus to be displayed in the ICHOR CLU, such as
    when `python ICHOR.py (specifically python3 ICHOR.py)` is ran
    
    :param title: The title of the menu
    :param options: A list of options to be displayed. Default is None. Options are usually added using `add_option` method.
    :param message: A message to be displayed at the top of the menu
    :param prompt: A set of characters that appear where user input will be taken
    :param refresh: matt_todo not sure how this refresh works, so I have not documented methods/variables which relate to it.
    :param auto_clear: Whether to clear the screen before a menu is shown. Default True.
    :param enable_problems: Whether to display any problems that ICHOR has found with the current setup.
    :param auto_close: Whether or not to close ICHOR once a function is executed.
    :param space: Whether to add a blank line at the bottom of the menu. This is added when the Back and Exit options are present.
    :param back: Whether to add a back option in the current menu in order to go to previous menu.
    :param exit: Whether to add an exit option to exit ICHOR.
    """

    def __init__(
        self,
        title: str = None,
        options: List = None,
        message: str = None,
        prompt: str = ">>",
        refresh: Callable = lambda *args: None,
        auto_clear: bool = True,
        enable_problems: bool = False,
        auto_close: bool = False,
        space: bool = False,
        back: bool = False,
        exit: bool = False,
    ):
        self.title = title
        self.options = None
        if options is None:
            options = []
        self.set_options(options)
        self.is_title_enabled = title is not None
        self.message = message
        self.is_message_enabled = message is not None
        self.refresh = None
        self.set_refresh(refresh)
        self.prompt = prompt
        self.is_open = None
        self.auto_clear = auto_clear
        self.auto_close = auto_close
        self.problems_enabled = enable_problems

        # keep track of things that are going to be displayed in a menu
        self.gap_ids = []
        self.message_ids = []
        self.wait_options = []
        self.close_options = []
        self.hidden_options = []

        self.space = space
        self.back = back
        self.exit = exit

    def set_options(self, options):
        """If a list of options to be displayed in the menu is passed when an instance of the class `Menu` is made, then this method is called.
        Usually, this method is not used but instead the `add_option` method is used instead once an instance has already been made.

        :param options: A list of tuples of options. Must have a label, name, and handler. See `add_option` method for details.
        """
        original = self.options
        self.options = {}
        try:
            for option in options:
                if not isinstance(option, tuple):
                    raise TypeError(option, "option is not a tuple")
                if len(option) < 2:
                    raise ValueError(option, "option is missing a handler")
                kwargs = option[3] if len(option) == 3 else {}
                self.add_option(option[0], option[1], kwargs)
        except (TypeError, ValueError) as e:
            self.options = original
            raise e

    def set_title(self, title: str) -> None:
        """Set the title of current menu that is displayed."""
        self.title = title

    def set_title_enabled(self, is_enabled: bool) -> None:
        """Enable or disable the title of the current menu that is displayed."""
        self.is_title_enabled = is_enabled

    def set_message(self, message: str) -> None:
        """Display a message at the top of the menu (such as errors, etc.)"""
        self.message = message

    def set_message_enabled(self, is_enabled: bool) -> None:
        """Enable or disable the message at the top of the menu."""
        self.is_message_enabled = is_enabled

    def set_prompt(self, prompt: str) -> None:
        """Set the prompt characters that are displayed where user input is typed in."""
        self.prompt = prompt

    def set_refresh(self, refresh) -> None:
        if not callable(refresh):
            raise TypeError(refresh, "refresh is not callable")
        self.refresh = refresh

    def clear_options(self) -> None:
        """Clear the current set of options that were stored (and which the user could select from), so that a new set of options can be displayed
        if the user is in another menu."""
        self.options = None

        self.gap_ids = []
        self.message_ids = []
        self.wait_options = []
        self.close_options = []
        self.hidden_options = []

        self.set_options([])

    def get_options(self, include_hidden=True) -> List[str]:
        """Returns the labels that the user can type, in order to navigate the menu."""
        return [
            label
            for label, option in self.options.items()
            if label not in self.gap_ids
            and label not in self.message_ids
            and (label not in self.hidden_options or include_hidden)
        ]

    def add_option(
        self,
        label: str,
        name: str,
        handler: Callable,
        kwargs=None,
        wait: bool = False,
        auto_close: bool = False,
        hidden: bool = False,
    ) -> None:
        #todo: do not know what the handler function is supposed to do exactly, so it is not documented
        #todo: do not know what the wait/wait options do exactly
        #todo: do not know what auto_close does, does it close the menu only or the whole ICHOR?
        """
        Add menu option that the user can select
        
        :param label: The letter/word that needs to be typed into the input prompt in order to go to the menu option
        :param name: The name of the option that can be selected by the user
        :param handler: A function which is going to perform the operation selected by the user, eg. submit_gjfs() will submit Gaussian gjf files.
        :param kwargs: Key word arguments to be passed to the `handler` function
        :param wait: Whether or not to wait for user input (press Enter) before the user can type in another input/navigate the menu.
        :param auto_close: Whether or not to close ICHOR once a function is executed.
        :param hidden: Whether or not to display this as an option in the menu or remain hidden (but can still be accessed to by the user)
        """
        if kwargs is None:
            kwargs = {}
        if not callable(handler):
            raise TypeError(handler, "handler is not callable")
        self.options[label] = (name, handler, kwargs) # add the option to the list of options
        if wait:
            self.wait_options.append(label)
        if auto_close:
            self.close_options.append(label)
        if hidden:
            self.hidden_options.append(label)

    def add_space(self) -> None:
        """Used to add spacing (blank lines) between options and other items in the menu."""
        gap_id = uuid4()
        self.gap_ids.append(gap_id)
        self.options[gap_id] = ("", "", {})

    def add_message(self, message, fmt={}) -> None:
        """Adds a text message to be displayed at the top of the menu."""
        message_id = uuid4()
        self.message_ids.append(message_id)
        self.options[message_id] = (message, fmt, {})

    # open the menu
    def run(self) -> None:
        """Calls the associated `input` method that displays the menu and waits for user input. Once the user enters a
        valid option, the handler function (wrapped in a lambda function) is returned as the variable `func`, along with
        boolean values for `wait` and `close`. Then, the lambda function is executed by `func()` causing the respective
        handler function inside to be executed with its arguments."""
        self.is_open = True
        while self.is_open:
            self.refresh(self)
            func, wait, close = self.input()
            if func == Menu.CLOSE: # if self.input() returns Menu.CLOSE, then set func to self.close
                func = self.close
            print()
            func()
            if close or self.auto_close:
                self.close()
            input("\nContinue... [Return]") if wait else None

    def close(self) -> None:
        """Closes the menu."""
        self.is_open = False

    def print_title(self) -> None:
        """Print the title to the screen."""
        print("#" * (len(self.title) + 4))
        print("# " + self.title + " #")
        print("#" * (len(self.title) + 4))
        print()

    def print_problems(self) -> None:
        # matt_todo: remove UsefulTools from here as it is not even imported. This method does not work right now?
        """Print problems found (such as with config files, etc.) at the top of the menu."""
        problems = ProblemFinder()
        problems.find()
        if len(problems) > 0:
            max_len = UsefulTools.count_digits(len(problems))
            s = "s" if len(problems) > 1 else ""
            print(f"Problem{s} Found:")
            print()
            for i, problem in enumerate(problems):
                print(
                    f"{i + 1:{str(max_len)}d}) "
                    + str(problem).replace(  # index problem  # print problem
                        "\n", "\n" + " " * (max_len + 2)
                    )
                )  # fix indentation
                print()

    def add_final_options(self, space=True, back=True, exit=True) -> None:
        """Add options to navigate to other ICHOR menus."""
        if space:
            self.add_space()
        if back:
            self.add_option("b", "Go Back", Menu.CLOSE)
        if exit:
            self.add_option("0", "Exit", sys.exit)

    #TODO: rename method to better describe what it does
    def longest_label(self) -> int:
        """Returns the length of the longest option. This is used to print out the options nicely."""
        lengths = [
            len(option) for option in self.get_options(include_hidden=False)
        ]
        return max(lengths)

    @classmethod
    def clear_screen(cls):
        os.system("cls" if os.name == "nt" else "clear")

    def show(self):
        """Clears the screen and shows an ICHOR menu with options that the user can select from."""
        if self.auto_clear:
            self.clear_screen()
        if self.problems_enabled:
            self.print_problems()
        if self.is_title_enabled:
            self.print_title()
        if self.is_message_enabled:
            print(self.message)
            print()
        label_width = self.longest_label()
        for label, option in self.options.items():
            if label not in self.gap_ids:
                if label in self.message_ids:
                    print(option[0].format(**option[1]))
                elif label not in self.hidden_options:
                    show_label = "[" + label + "] "
                    print(f"{show_label:<{label_width + 3}s}" + option[0])
            else:
                print()
        print()

    # matt_todo: this method is not used anywhere in ICHOR, so do not think it is needed.
    def func_wrapper(self, func):
        func()
        self.close()

    # show the menu
    # get the option index from the input
    # return the corresponding option handler
    def input(self) -> Tuple[Callable, bool, bool]:
        """Shows the menu and waits for user input into the prompt. Once a user input is detected, it returns the
        handler function (with its respective key word arguments), as well as boolean values whether depending on
        whether or not there are wait or close options associated with the handler function.

        .. note::
            A lambda function (unnamed function) which has NOT been executed is returned by this method. This lambda function
            contains the handler function. See the `run` method, where the lambda function is actually executed and thus the
            inner handler function is executed then, not here.
        """
        # if no options then close the menu
        if len(self.options) == 0:
            return Menu.CLOSE

        # show the menu
        self.show()

        # allow for user input to select options
        with ListCompleter(self.get_options()): # get the labels to be autocompleted
            while True:
                try:
                    index = str(input(self.prompt + " ")).strip() # get the index of the option
                    option = self.options[index] # get the values from the self.options dictionary
                    handler = option[1] # the first value in the returned list is the function which handles the operation
                    if handler == Menu.CLOSE:
                        return Menu.CLOSE, False, False
                    kwargs = option[2] # the second option is any key word arguments to be passed to the handler function
                    return (
                        lambda: handler(**kwargs),
                        index in self.wait_options,  # returns True or False
                        index in self.close_options,  # returns True or False
                    )
                except (ValueError, IndexError):
                    # matt_todo: Here self.input() is executed, but shouldn't the return value be self.input, False, False
                    # so then going to the .run method func is self.input which is later executed?
                    return self.input(), False, False 
                except KeyError:
                    print("Error: Invalid input")

    def CLOSE(self):
        """Used to determine if the current menu should be closed."""
        pass

    def __enter__(self):
        """
        To be used when a Menu is constructed as a context manager. Returns the instance of a menu.
        For example, in main_menu.py `with Menu(f"{path} Menu", space=True, back=True, exit=True) as menu:`
        is used where `with Menu(f"{path} Menu", space=True, back=True, exit=True)` is going to make a new
        instance of class `Menu` which is going to be stored in the variable `menu`. Then, this `menu`
        object can be manipulated (i.e. can have options added to it) inside the `with` block.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Once the `menu`'s `with` context manager block ends, this `__exit__ method is automatically called. It adds
        options to navigate to other menus as well as to exit ICHOR. Finally, the menu's `run` method is called, which
        prints out the menu to the terminal with the options that the user can select from."""
        if any([self.space, self.back, self.exit]):
            self.add_final_options(self.space, self.back, self.exit)
        self.run()