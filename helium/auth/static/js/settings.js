/**
 * Copyright (c) 2017 Helium Edu.
 *
 * JavaScript for /settings page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.0
 */

/**
 * Create the HeliumSettings persistence object.
 *
 * @constructor construct the HeliumSettings persistence object
 */
function HeliumSettings() {
    "use strict";

    var self = this;

    this.create_externalcalendar = function (id, title, url, shown_on_calendar, color) {
        var row = $('<tr id="externalcalendar-' + id + '">');
        row.append($('<td>').append('<a class="cursor-hover external-title">' + title + '</a>'));
        row.append($('<td class="hidden-480">').append('<a class="cursor-hover external-url">' + url + '</a>'));
        row.append($('<td>').append('<input type="checkbox" class="ace" /><span class="lbl" />'));
        row.append($('<td>').append($('<select class="hide color-picker">' + $("#id_events_color").html() + '</select>')));
        row.append($('<td>').append('<div class="btn-group"><button type="button" class="btn btn-xs btn-danger delete-externalcalendar"><i class="icon-trash bigger-120"></i></button></div></td></tr>'));

        $("#externalcalendars-table-body").append(row);

        row.find(".color-picker").simplecolorpicker({
            picker: true,
            theme: "glyphicons"
        });
        row.find(".color-picker").simplecolorpicker("selectColor", color);
        row.find(".external-title").editable({
            type: "text",
            tpl: '<input type="text" maxlength="255">'
        });
        row.find(".external-url").editable({
            type: "text",
            tpl: '<input type="text" maxlength="255">'
        });
        row.find(".delete-externalcalendar").on("click", self.delete_externalcalendar);

        if ($("#externalcalendars-table-body").children().length === 2) {
            $("#no-externalcalendars").hide();
        }
    };

    this.delete_externalcalendar = function () {
        var row = $(this).parent().parent().parent();
        row.hide("fast", function () {
            $(this).remove();
            if ($("#externalcalendars-table-body").children().length === 1) {
                $("#no-externalcalendars").show();
            }

            // TODO: need to save this off so that the delete is persisted on save
        });
    };

    self.save_externalcalendars = function (form) {
        var dom_id, id, unsaved_string;

        $.each(form.find("tr[id^='externalcalendar-']"), function () {
            dom_id = $(this).attr("id");
            id = dom_id.split("-");
            if (dom_id.indexOf("-unsaved") !== -1) {
                id = id[id.length - 2];
            } else {
                id = id[id.length - 1];
            }
            unsaved_string = "";
            if (dom_id.indexOf("-unsaved") !== -1) {
                unsaved_string = "-unsaved";
            }
            var data = {
                title: form.find("#externalcalendar-" + id + unsaved_string + "-title").html(),
                url: form.find("#externalcalendar-" + id + unsaved_string + "-url").html(),
                color: form.find("#externalcalendar-" + id + unsaved_string + "-color-picker").val(),
                shown_on_calendar: form.find("#externalcalendar-" + id + unsaved_string + "-enabled").is(":checked")
            };
            $.ajax({
                async: false,
                context: form,
                data: data,
                type: 'POST',
                url: '/api/feed/externalcalendars/',
                error: function () {
                    // TODO: show errors
                }
            });
        });
    };

    $("#create-externalcalendar").on("click", function () {
        self.create_externalcalendar(-1, 'New Source', 'http://www.externalcalendar.com/feed', false, $($("#id_events_color option")[Math.floor(Math.random() * $("#id_events_color option").length)]).val());
    });

    $("#preferences-form").submit(function (e) {
        // Prevent default submit
        e.preventDefault();
        e.returnValue = false;

        $("#loading-preferences").spin(helium.SMALL_LOADING_OPTS);

        $.ajax().always(function () {
            var form = $("#preferences-form"), data = form.serializeArray();

            self.save_externalcalendars(form);

            $.ajax({
                async: false,
                context: form,
                data: data,
                type: 'PUT',
                url: '/api/user/settings',
                error: function () {
                    $("#loading-preferences").spin(false);

                    // TODO: show errors
                },
                success: function () {
                    $("#loading-preferences").spin(false);
                }
            });
        });
    });

    $("#personal-form").submit(function (e) {
        // Prevent default submit
        e.preventDefault();
        e.returnValue = false;

        $("#loading-personal").spin(helium.SMALL_LOADING_OPTS);

        $.ajax().always(function () {
            var form = $("#personal-form"), data = form.serializeArray();

            $.ajax({
                async: false,
                context: form,
                data: data,
                type: 'PUT',
                url: '/api/user/profile',
                error: function () {
                    $("#loading-personal").spin(false);

                    // TODO: show errors
                },
                success: function () {
                    $("#loading-personal").spin(false);
                }
            });
        });
    });

    $("#account-form").submit(function (e) {
        // Prevent default submit
        e.preventDefault();
        e.returnValue = false;

        $("#loading-account").spin(helium.SMALL_LOADING_OPTS);

        $.ajax().always(function () {
            var form = $("#account-form"), data = form.serializeArray();

            $.ajax({
                async: false,
                context: form,
                data: data,
                type: 'PUT',
                url: '/api/user',
                error: function () {
                    $("#loading-account").spin(false);

                    // TODO: show errors
                },
                success: function () {
                    $("#loading-account").spin(false);
                }
            });
        });
    });

    $("#delete-account").on("click", function () {
        bootbox.dialog({
            title: "To permanently delete your Helium account <em>and all data you have stored in Helium</em>, confirm your password below.",
            message: '<input id="delete-account" name="delete-account" type="password" class="form-control" />',
            inputType: "password",
            closeButton: true,
            buttons: {
                cancel: {
                    label: "Cancel",
                    className: "btn-default"
                },
                success: {
                    label: "OK",
                    className: "btn-primary",
                    callback: function () {
                        $("#loading-account").spin(helium.SMALL_LOADING_OPTS);

                        var data = {
                            "username": helium.USER_PREFS.username,
                            "email": helium.USER_PREFS.email,
                            "password": $("input[name='delete-account']").val()
                        };

                        $.ajax({
                            async: false,
                            data: data,
                            type: 'DELETE',
                            url: '/api/user',
                            error: function () {
                                $("#loading-account").spin(false);

                                // TODO: show errors
                            },
                            success: function () {
                                $("#loading-account").spin(false);

                                // TODO: set a cookie so a message is shown about the delete being successful after logout

                                window.location = "/logout";
                            }
                        });
                    }
                }
            }
        });
    });
}

// Initialize HeliumSettings and give a reference to the Helium object
helium.settings = new HeliumSettings();

$(document).ready(function () {
    "use strict";

    $("#loading-preferences").spin(false);
    $("#loading-personal").spin(false);
    $("#loading-account").spin(false);

    $("#id_phone_carrier").chosen({width: "100%", search_contains: true, no_results_text: "No carriers match"});
    $("#id_time_zone").chosen({width: "100%", search_contains: true, no_results_text: "No time zones match"});
    $("#id_events_color").simplecolorpicker({picker: true, theme: "glyphicons"});

    if ($(".externalcalendars-help").length > 0) {
        $(".externalcalendars-help").popover({html: true}).data("bs.popover").tip().css("z-index", 1060);
        $(".externalcalendars-help").on("click", function () {
            window.open("https://support.google.com/calendar/answer/37648?hl=en");
        });
    }

    // TODO: perform a GET on externalcalendars and call "create" for any that already exist

    // TODO: preload form fields

    // TODO: show status of verified or pending verifications for email

    // TODO: show status of verified or pending verifications for phone (if all is verified, hide verification input field)
});