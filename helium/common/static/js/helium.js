/**
 * Copyright (c) 2017 Helium Edu.
 *
 * Dynamic functionality shared among all pages.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.0
 */

/**
 * Create the Helium persistence object.
 *
 * @constructor construct the Helium persistence object
 */
function Helium() {
    "use strict";

    // Variables to establish the current request/page the user is accessing
    this.SITE_HOST = location.host + "/";
    this.SITE_URL = location.protocol + "//" + this.SITE_HOST;
    this.CURRENT_PAGE_URL = document.URL;
    this.CURRENT_PAGE = this.CURRENT_PAGE_URL.split(this.SITE_URL)[1];
    if (this.CURRENT_PAGE.substr(-1) === "/") {
        this.CURRENT_PAGE = this.CURRENT_PAGE.substr(0, this.CURRENT_PAGE.length - 1);
    }
    // This object gets initialized in the base template
    this.USER_PREFS = {};

    // Date/Time formats used between the client and server
    this.HE_DATE_STRING_SERVER = "YYYY-MM-DD";
    this.HE_TIME_STRING_SERVER = "HH:mm:ss";
    this.HE_DATE_TIME_STRING_SERVER = this.HE_DATE_STRING_SERVER + " " + this.HE_TIME_STRING_SERVER;
    this.HE_DATE_STRING_CLIENT = "MMM D, YYYY";
    this.HE_TIME_STRING_CLIENT = "h:mm A";
    this.HE_DATE_TIME_STRING_CLIENT = this.HE_DATE_STRING_CLIENT + " " + this.HE_TIME_STRING_CLIENT;
    this.HE_REMINDER_DATE_STRING = "ddd, MMM DD";
    this.ajax_error_occurred = false;

    // Options for loading spin presets
    this.LARGE_LOADING_OPTS = {
        lines: 13,
        length: 10,
        width: 5,
        radius: 15,
        corners: 1,
        rotate: 0,
        direction: 1,
        color: "#000",
        speed: 1,
        trail: 60,
        shadow: false,
        hwaccel: false,
        zIndex: 200,
        top: "200px",
        left: "auto"
    };
    this.SMALL_LOADING_OPTS = {
        lines: 13,
        length: 4,
        width: 2,
        radius: 4,
        corners: 1,
        rotate: 0,
        direction: 1,
        color: "#000",
        speed: 1,
        trail: 60,
        shadow: false,
        hwaccel: false,
        className: "loading-mini",
        zIndex: 200,
        top: "-14px",
        left: "-20px"
    };
    this.FILTER_LOADING_OPTS = {
        lines: 13,
        length: 4,
        width: 2,
        radius: 4,
        corners: 1,
        rotate: 0,
        direction: 1,
        color: "#000",
        speed: 1,
        trail: 60,
        shadow: false,
        hwaccel: false,
        className: "loading-inline",
        zIndex: 200,
        top: "3px",
        left: "5px"
    };

    // Persistence objects within Helium
    this.planner_api = null;
    this.settings = null;
    this.classes = null;
    this.calendar = null;
    this.materials = null;
    this.grades = null;
    this.school = null;

    /**
     * From a given string (which may be a mathematical operation), convert the string to a percentage string.
     *
     * @param value the string to convert to a percentage value
     * @param last_good_value the last good percentage string value
     * @return the percentage value from the given string, or the last_good_value, if the given string was invalid
     */
    this.calculate_to_percent = function (value, last_good_value) {
        var split;
        // Remove any spaces before we try to be smart
        value = value.replace(/\s/g, "");
        // Drop the percent, if it exists
        if (value.match(/%$/)) {
            value = value.substring(0, value.length - 1);
        }
        // If this is a ratio, convert it to a percent
        if (value.indexOf("/") !== -1) {
            split = value.split("/");
            if (!isNaN(split[0]) && !isNaN(split[1])) {
                value = ((split[0] / split[1]) * 100).toString();
            } else {
                value = last_good_value;
            }
        } else if (isNaN(value)) {
            // Not sure what this value is, so drop in the last known value
            value = last_good_value;
        }
        // If the value we have is negative, drop in the last know value
        if (value < 0) {
            value = last_good_value;
        }
        // Ensure no more than three digits to the left of the decimal
        if (value.split(".")[0].length > 3) {
            value = last_good_value;
        }
        // Set the percentage string
        if (value !== "" && !isNaN(value)) {
            value = Math.round(value * 100) / 100 + "%";
        }
        return value;
    };

    /**
     * This function converts a database grade (in a fractional format) into a grade for display. If the grade is out
     * of 100, a simple percent is returned, otherwise the grade and points are returned.
     *
     * @param grade
     */
    this.grade_for_display = function(grade) {
        var split, value;
        if (grade.indexOf("/") !== -1) {
            split = grade.split("/");
            value = (parseFloat(split[0]) / parseFloat(split[1])) * 100;
        } else {
            value = grade;
        }

        return (Math.round(value * 100) / 100) + "%";
    };

    /**
     * Checks if data from the return of an Ajax call is valid or contains an error message.
     *
     * Note that value comparisons in this function are intentionally fuzzy, as they returned data type may not
     * necessarily be know.
     *
     * @param data the returned data object
     */
    this.is_data_invalid = function(data) {
        return (data == undefined || (data.length === 1 && (data[0].hasOwnProperty("err_msg"))));
    };

    /**
     * Checks if data from the return of an Ajax call contains a single err_msg field.
     *
     * Note that value comparisons in this function are intentionally fuzzy, as they returned data type may not
     * necessarily be know.
     *
     * @param data the returned data object
     */
    this.data_has_err_msg = function(data) {
        return data != undefined && data.length === 1 && data[0].hasOwnProperty("err_msg");
    };

    this.bytes_to_size = function(bytes) {
        var sizes = ['bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) {
            return '0 ' + sizes[0];
        }
        var i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
    };

    /**
     * Retrieve the string with proper HTML (for table view) for comments.
     */
    this.get_comments_with_link = function (comment_str) {
        return comment_str.replace(/(http|ftp|https):\/\/([-\w_]+(?:(?:\.[-\w_]+)+))([-\w\.,@?^=%&amp;:/~\+#]*[-\w\@?^=%&amp;/~\+#])?/g, function (str) {
            return "<a target=\"_blank\" class=\"material-with-link\" href=\"" + str + "\">" + str + "</a>";
        });
    };
}

// Be responsible; don't clutter the global namespace
(function () {
    "use strict";

    $(".reminder-close").on("click", function () {
        helium.ajax_error_occurred = false;

        var id = $(this).parent().attr("id").split("reminder-popup-")[1], data = {'sent': true}, reminder_div = $(this).parent();
        helium.planner_api.edit_reminder(function (data) {
            if (helium.is_data_invalid(data)) {
                helium.ajax_error_occurred = true;

                if (helium.data_has_err_msg(data)) {
                    bootbox.alert(data[0].err_msg);
                } else {
                    bootbox.alert("Oops, an unknown error has occurred. If the error persists, <a href=\"/support\">contact support</a>.");
                }
            } else {
                var new_count = parseInt($("#reminder-bell-count").text()) - 1;
                reminder_div.hide();

                $("#reminder-bell-count, #reminder-bell-alt-count").text(new_count);
                if (new_count === 0) {
                    $("#reminder-bell-alt-count").hide("fast");
                }
            }
        }, id, data);
    });
}());

// Initialize the Helium object
var helium = new Helium();