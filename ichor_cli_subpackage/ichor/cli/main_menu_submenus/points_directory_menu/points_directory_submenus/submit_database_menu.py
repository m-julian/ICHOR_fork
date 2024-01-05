from dataclasses import dataclass

import ichor.cli.global_menu_variables
import ichor.hpc.global_variables
from consolemenu.items import FunctionItem
from ichor.cli.console_menu import add_items_to_menu, ConsoleMenu
from ichor.cli.menu_description import MenuDescription
from ichor.cli.menu_options import MenuOptions
from ichor.cli.useful_functions import (
    single_or_many_points_directories,
    user_input_bool,
    user_input_restricted,
)
from ichor.hpc.main.database import AVAILABLE_DATABASE_FORMATS, submit_make_database

SUBMIT_DATABASE_MENU_DESCRIPTION = MenuDescription(
    "Database Menu",
    subtitle="Use this menu to make a database from PointsDirectory.\n",
)

# TODO: possibly make this be read from a file
SUBMIT_DATABASE_MENU_DEFAULTS = {
    "default_database_format": "sqlite",
    "default_submit_on_compute": True,
}


# dataclass used to store values for SubmitAIMALLMenu
@dataclass
class SubmitDatabaseMenuOptions(MenuOptions):

    selected_database_format: str
    selected_submit_on_compute: bool


# initialize dataclass for storing information for menu
submit_database_menu_options = SubmitDatabaseMenuOptions(
    *SUBMIT_DATABASE_MENU_DEFAULTS.values()
)


# class with static methods for each menu item that calls a function.
class SubmitDatabaseFunctions:
    @staticmethod
    def select_database():
        """Asks user to update the ethod for AIMALL. The method
        needs to be added to the WFN file so that AIMALL does the correct
        calculation."""

        submit_database_menu_options.selected_database_format = user_input_restricted(
            AVAILABLE_DATABASE_FORMATS.keys(),
            "Choose a database format: ",
            submit_database_menu_options.selected_database_format,
        )

    @staticmethod
    def select_submit_on_compute():
        """
        Asks user whether or not to submit database making on compute.
        """

        submit_database_menu_options.selected_submit_on_compute = user_input_bool(
            "Submit on compute (yes/no): ",
            submit_database_menu_options.selected_submit_on_compute,
        )

    @staticmethod
    def points_directory_to_database():
        """Converts the current given PointsDirectory to a SQLite3 database. Can be submitted on compute
        and works for one `PointsDirectory` or parent directory containing many `PointsDirectory`-ies"""

        is_parent_directory_to_many_points_directories = (
            single_or_many_points_directories()
        )

        database_format, submit_on_compute = (
            submit_database_menu_options.selected_database,
            submit_database_menu_options.selected_submit_on_compute,
        )

        submit_make_database(
            ichor.cli.global_menu_variables.SELECTED_POINTS_DIRECTORY_PATH,
            database_format,
            is_parent_directory_to_many_points_directories,
            submit_on_compute,
        )


# make menu items
# can use lambda functions to change text of options as well :)
submit_database_menu_items = [
    FunctionItem(
        "Change database format",
        SubmitDatabaseFunctions.select_database,
    ),
    FunctionItem(
        "Change submit to compute",
        SubmitDatabaseFunctions.select_submit_on_compute,
    ),
    FunctionItem(
        "Make database",
        SubmitDatabaseFunctions.points_directory_to_database,
    ),
]

# initialize menu
submit_database_menu = ConsoleMenu(
    this_menu_options=submit_database_menu_options,
    title=SUBMIT_DATABASE_MENU_DESCRIPTION.title,
    subtitle=SUBMIT_DATABASE_MENU_DESCRIPTION.subtitle,
    prologue_text=SUBMIT_DATABASE_MENU_DESCRIPTION.prologue_description_text,
    epilogue_text=SUBMIT_DATABASE_MENU_DESCRIPTION.epilogue_description_text,
    show_exit_option=SUBMIT_DATABASE_MENU_DESCRIPTION.show_exit_option,
)

add_items_to_menu(submit_database_menu, submit_database_menu_items)
