from ichor.cli.analysis_menus.analysis_menu import analysis_menu
from ichor.cli.general_menus.options_menu import options_menu
from ichor.cli.general_menus.queue_menu import queue_menu
from ichor.cli.machine_learning_menus.per_menu import auto_run_per_menu
from ichor.cli.points_directory_menu import (
    custom_points_directory_menu,
    points_directory_menu,
)
from ichor.cli.tools_menu import tools_menu
from ichor.core.menu.menu import Menu
from ichor.hpc import FILE_STRUCTURE
from ichor.hpc.auto_run.standard_auto_run import auto_run_from_menu
from ichor.hpc.main.active_learning import active_learning


def main_menu():
    print("here")
    with Menu("ICHOR Main Menu", back=False) as menu:
        menu.add_option(
            "1",
            "Training Set Menu",
            # the handler function in this case is points_directory_menu. This function gets called when the user selects option 1 in the menu.
            points_directory_menu,
            # give key word arguments which are passed to the handler function
            kwargs={
                "path": FILE_STRUCTURE["training_set"]
            },  # get the Path of the training set from GLOBALS.FILE_STRUCTURE
        )
        menu.add_option(
            "2",
            "Sample Pool Menu",
            points_directory_menu,
            kwargs={"path": FILE_STRUCTURE["sample_pool"]},
        )
        menu.add_option(
            "3",
            "Validation Set Menu",
            points_directory_menu,
            kwargs={"path": FILE_STRUCTURE["validation_set"]},
        )
        menu.add_option(
            "4",
            "Active Learning",
            active_learning,
            kwargs={
                "model_directory": FILE_STRUCTURE["models"],
                "sample_pool_directory": FILE_STRUCTURE["sample_pool"],
            },
        )
        menu.add_blank()  # add a blank line
        menu.add_option(
            "r",
            "Auto Run",
            auto_run_from_menu,
        )
        menu.add_option("p", "Per-Value Auto Run", auto_run_per_menu)
        menu.add_blank()
        menu.add_option(
            "c", "Custom PointsDirectory Menu", custom_points_directory_menu
        )
        menu.add_option("a", "Analysis Menu", analysis_menu)
        menu.add_option("o", "Options Menu", options_menu)
        menu.add_option("t", "Tools Menu", tools_menu)
        menu.add_option("q", "Queue Menu", queue_menu)
