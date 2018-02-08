/**
 * Copyright (c) 2018 Helium Edu.
 *
 * Dynamic functionality shared among all pages.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.2.0
 */

var CSRF_TOKEN = Cookies.get("csrftoken");

// Initialize AJAX configuration
function csrfSafeMethod(method) {
    "use strict";

    // These HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        "use strict";

        if (!csrfSafeMethod(settings.type)) {
            // Send the token to same-origin, relative URLs only.
            // Send the token only if the method warrants CSRF protection
            // Using the CSRFToken value acquired earlier
            xhr.setRequestHeader("X-CSRFToken", CSRF_TOKEN);
        }
    },
    contentType: "application/json; charset=UTF-8"
});

/**
 * Create the Helium persistence object.
 *
 * @constructor construct the Helium persistence object
 */
function Helium() {
    "use strict";

    this.REMINDER_OFFSET_TYPE_CHOICES = [
        "minutes",
        "hours",
        "days",
        "weeks"
    ];
    this.REMINDER_TYPE_CHOICES = [
        "Popup",
        "Email",
        "Text"
    ];

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
    this.HE_DATE_STRING_CLIENT = "MMM D, YYYY";
    this.HE_TIME_STRING_CLIENT = "h:mm A";
    this.HE_DATE_TIME_STRING_CLIENT = this.HE_DATE_STRING_CLIENT + " " + this.HE_TIME_STRING_CLIENT;
    this.HE_REMINDER_DATE_STRING = "ddd, MMM DD";

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
    this.grade_for_display = function (grade) {
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
    this.data_has_err_msg = function (data) {
        return data != undefined && data.length === 1 && data[0].hasOwnProperty("err_msg");
    };

    /**
     * Extract the error message from a response already know to have an error.
     *
     * @returns An HTML formatted error response.
     */
    this.get_error_msg = function (data) {
        var response = data[0];
        // If responseJSON exists, we can likely find a more detailed message to be parsed
        if (response.hasOwnProperty('jqXHR') && response.jqXHR.hasOwnProperty('responseJSON')) {
            if (response.jqXHR.responseJSON.hasOwnProperty('detail')) {
                return response.jqXHR.responseJSON.detail;
                // TODO: we could parse more API responses here, but may make more sense to just wait and improve error
                // handling when we rebuild the entire UI
            } else {
                return response.err_msg
            }
        } else {
            return response.err_msg
        }
    };

    this.bytes_to_size = function (bytes) {
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

    this.clear_form_errors = function (selector) {
        $("#status_" + selector.split("-form")[0]).html("").addClass("hidden");

        $("#" + selector + " *").filter(':input').each(function (index, data) {
            if ($(data).attr("id") !== undefined) {
                $($(data).parent()).removeClass("has-error");
                $("#status_" + $(data).attr("id").substring(3)).html("").addClass("hidden");
            }
        });
    };

    this.show_error = function (form_id, selector, error_msg) {
        if ($("#status_" + selector).length > 0) {
            $($("#id_" + selector).parent()).addClass("has-error");
            $("#status_" + selector).html(error_msg).removeClass("hidden");
        } else {
            $("#status_" + form_id).html(error_msg).addClass("alert-warning").removeClass("hidden");
        }
    };

    this.add_reminder_to_page = function (data) {
        var type = "system";
        var start = moment(data.start_of_range);
        var id_str = "reminder-system-" + data.id;
        if (data.homework !== null) {
            type = "homework";
            id_str = "reminder-for-homework-" + data.homework.id;
            start = moment(data.homework.start);
        } else if (data.event !== null) {
            type = "event";
            id_str = "reminder-for-event-" + data.event.id;
            start = moment(data.event.start);
        }

        var list_item = $('<li id="reminder-popup-' + data.id + '" class="reminder-popup"><button type="button" class="close reminder-close"><i class="icon-remove"></i></button></li>');
        var reminder_body = $('<span class="reminder-msg-body' + (location.href.indexOf('/planner/calendar') !== -1 ? ' cursor-hover' : '') + '" id="' + id_str + '"></span>');
        list_item.append(reminder_body);

        var msg_body = $('<span class="msg-body">');
        reminder_body.append(msg_body);
        if (type === "homework") {
            msg_body.append('<span class="msg-title"><span class="blue">(' + data.homework.course.title + ') ' + data.homework.title + '</span> ' + data.message + '</span>');
        } else if (type === "event") {
            msg_body.append('<span class="msg-title"><span class="blue">(Event) ' + data.event.title + '</span> ' + data.message + '</span>');
        }

        var msg_time = $('<span class="msg-time">');
        reminder_body.append(msg_time);
        msg_time.append('<i class="icon-time"></i>');
        msg_time.append('<span>&nbsp;' + start.format(helium.HE_REMINDER_DATE_STRING) + ' at ' + start.format(helium.HE_TIME_STRING_CLIENT) + '</span>');

        list_item.find('.reminder-close').on("click", function () {
            helium.ajax_error_occurred = false;

            var put_data = {
                'sent': true
            }, reminder_div = $(this).parent();
            helium.planner_api.edit_reminder(function (data) {
                if (helium.data_has_err_msg(data)) {
                    helium.ajax_error_occurred = true;

                    bootbox.alert(helium.get_error_msg(data));
                } else {
                    var new_count = parseInt($("#reminder-bell-count").text()) - 1;
                    reminder_div.hide();

                    $("#reminder-bell-count").html(new_count + " Reminder" + (new_count > 1 ? "s" : ""));
                    $("#reminder-bell-alt-count").html(new_count);
                    if (new_count === 0) {
                        $("#reminder-bell-alt-count").hide("fast");
                    }
                }
            }, data.id, put_data, true, true);
        });
        if (location.href.indexOf('/planner/calendar') !== -1) {
            list_item.find('[id^="reminder-for-"]').on("click", function () {
                var id = $(this).attr("id").split("reminder-for-")[1];
                if (id.indexOf("event-") !== -1) {
                    id = id.replace("-", "_");
                } else {
                    id = id.split("-")[1];
                }

                helium.calendar.current_calendar_item = $("#calendar").fullCalendar("clientEvents", [id])[0];
                // First resort is to look in the calendar's cache, but if the event isn't found there we'll have to look it
                // up in the database
                if (helium.calendar.current_calendar_item === undefined) {
                    helium.calendar.loading_div.spin(helium.SMALL_LOADING_OPTS);

                    var callback = function (data) {
                        if (helium.data_has_err_msg(data)) {
                            helium.ajax_error_occurred = true;
                            helium.calendar.loading_div.spin(false);

                            bootbox.alert(helium.get_error_msg(data));
                        } else {
                            helium.calendar.loading_div.spin(false);

                            helium.calendar.current_calendar_item = data;
                            helium.calendar.edit_calendar_item_btn(helium.calendar.current_calendar_item);
                        }
                    };
                    if (id.indexOf("event") !== -1) {
                        helium.planner_api.get_event(callback, id, true, true);
                    } else {
                        helium.planner_api.get_homework_by_id(function (data) {
                            helium.planner_api.get_homework(callback, data.course.course_group, data.course.id, id, true, true);
                        }, id, true);
                    }
                } else {
                    helium.calendar.edit_calendar_item_btn(helium.calendar.current_calendar_item);
                }
            });
        }

        $($($("#reminder-bell-count").parent()).parent()).append(list_item);
    };

    this.process_reminders = function (data) {
        if (!helium.data_has_err_msg(data)) {
            $("[id^='reminder-popup-']").remove();

            $.each(data, function (i, reminder_data) {
                helium.add_reminder_to_page(reminder_data);
            });

            $("#reminder-bell-count").html(data.length + " Reminder" + (data.length > 1 ? "s" : ""));
            $("#reminder-bell-alt-count").html(data.length);
            if (data.length > 0) {
                $("#reminder-bell-alt-count").show("fast");
            } else {
                $("#reminder-bell-alt-count").hide("fast");
            }
        }
    };
}

// Initialize the Helium object
var helium = new Helium();

if (typeof USER_ID !== 'undefined') {
    $.ajax({
        type: "GET",
        url: "/api/auth/users/" + USER_ID + "/",
        async: false,
        dataType: "json",
        success: function (data) {
            $.extend(helium.USER_PREFS, data);
        }
    });

    moment.tz.setDefault(helium.USER_PREFS.settings.time_zone);
}