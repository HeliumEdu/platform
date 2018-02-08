/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript for /settings page.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.2.0
 */

/**
 * Create the HeliumSettings persistence object.
 *
 * @constructor construct the HeliumSettings persistence object
 */
function HeliumSettings() {
    "use strict";

    var self = this;

    self.to_delete = [];

    self.populate_externalcalendars = function () {
        $('tr[id^="externalcalendar-"]').each(function () {
            $(this).remove();
        });

        $.ajax({
            type: "GET",
            url: "/api/feed/externalcalendars/",
            async: false,
            dataType: "json",
            success: function (data) {
                $.each(data, function (key, externalcalendar) {
                    helium.settings.create_externalcalendar(externalcalendar.id, externalcalendar.title, externalcalendar.url, externalcalendar.shown_on_calendar, externalcalendar.color);
                });
            }
        });

        if ($("#externalcalendars-table-body").children().length === 1) {
            $("#no-externalcalendars").show();
        }
    };

    self.email_pending = function (email_changing) {
        ($("#id_email_verification_status").html('<i class="icon-time bigger-110 orange"></i> Pending verification of ' + email_changing));
    };

    self.phone_pending = function (phone_changing) {
        $($("#id_phone_verification_status").html('<i class="icon-time bigger-110 orange"></i> Pending verification of ' + phone_changing));
        $("#phone_verification_row").show("fast");
    };

    self.create_externalcalendar = function (id, title, url, shown_on_calendar, color) {
        var row = $('<tr id="externalcalendar-' + id + '">');
        row.append($('<td>').append('<a class="cursor-hover external-title">' + title + '</a>'));
        row.append($('<td class="hidden-480">').append('<a class="cursor-hover external-url">' + url + '</a>'));
        row.append($('<td>').append('<input type="checkbox" class="ace shown-on-calendar" ' + (shown_on_calendar ? 'checked="checked"' : '') + '/><span class="lbl" />'));
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

    self.delete_externalcalendar = function () {
        var row = $(this).parent().parent().parent(), dom_id, id;
        row.hide("fast", function () {
            dom_id = $(this).attr("id");
            id = dom_id.split("-");
            id = id[id.length - 1];
            if (id !== "null") {
                self.to_delete.push(id);
            }

            $(this).remove();
            if ($("#externalcalendars-table-body").children().length === 1) {
                $("#no-externalcalendars").show();
            }
        });
    };


    self.save_externalcalendars = function (form) {
        var dom_id, id;

        $.each(form.find("tr[id^='externalcalendar-']"), function () {
            dom_id = $(this).attr("id");
            id = dom_id.split("-");
            id = id[id.length - 1];
            var data = {
                title: $(this).find(".external-title").html(),
                url: $(this).find(".external-url").html(),
                color: $(this).find(".color-picker").val(),
                shown_on_calendar: $(this).find(".shown-on-calendar").is(":checked")
            };
            if (id === "null") {
                $.ajax({
                    async: false,
                    context: form,
                    data: JSON.stringify(data),
                    type: 'POST',
                    url: '/api/feed/externalcalendars/',
                    error: function (xhr) {
                        $("#status_preferences").html('Oops, an error occurred while saving changes to external calendars. Was the URL valid?').addClass("alert-warning").removeClass("hidden");
                    }
                });
            } else {
                $.ajax({
                    async: false,
                    context: form,
                    data: JSON.stringify(data),
                    type: 'PUT',
                    url: '/api/feed/externalcalendars/' + id + '/',
                    error: function (xhr) {
                        $("#status_preferences").html('Oops, an error occurred while saving changes to external calendars. Was the URL valid?').addClass("alert-warning").removeClass("hidden");
                    }
                });
            }
        });
    };

    $("#create-externalcalendar").on("click", function () {
        self.create_externalcalendar("null", 'Holidays', 'https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics', false, $($("#id_events_color option")[Math.floor(Math.random() * $("#id_events_color option").length)]).val());
    });

    $("#preferences-form").submit(function (e) {
        // Prevent default submit
        e.preventDefault();
        e.returnValue = false;

        $("#loading-preferences").spin(helium.SMALL_LOADING_OPTS);

        helium.clear_form_errors($(this).attr("id"));

        $.ajax().always(function () {
            var form = $("#preferences-form"), data = form.serializeArray();
            data.push({"name": "show_getting_started", "value": helium.USER_PREFS.settings.show_getting_started});
            data.push({
                "name": "receive_emails_from_admin",
                "value": helium.USER_PREFS.settings.receive_emails_from_admin
            });
            data.push({"name": "private_slug", "value": helium.USER_PREFS.settings.private_slug});

            self.save_externalcalendars(form);

            $.each(self.to_delete, function (index, id) {
                $.ajax({
                    async: false,
                    type: 'DELETE',
                    url: '/api/feed/externalcalendars/' + id + '/',
                    error: function (xhr) {
                        // TODO: show errors
                    }
                });
            });
            self.to_delete = [];

            self.populate_externalcalendars();

            $.ajax({
                async: false,
                context: form,
                data: data,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                type: 'PUT',
                url: '/api/auth/users/' + helium.USER_PREFS.id + '/settings/',
                error: function (xhr) {
                    $.each(xhr.responseJSON, function (key, value) {
                        helium.show_error(key, value);
                    });

                    $("#loading-preferences").spin(false);
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

        helium.clear_form_errors($(this).attr("id"));

        $.ajax().always(function () {
            var form = $("#personal-form"), data = form.serializeArray();

            $.ajax({
                async: false,
                context: form,
                data: data,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                type: 'PUT',
                url: '/api/auth/users/' + helium.USER_PREFS.id + '/profile/',
                error: function (xhr) {
                    $.each(xhr.responseJSON, function (key, value) {
                        helium.show_error(key, value);
                    });

                    $("#loading-personal").spin(false);
                },
                success: function (data) {
                    if (data.phone_changing || data.phone_carrier_changing) {
                        self.phone_pending(data.phone_changing);
                    } else {
                        $("#id_phone").val(data.phone);
                        $("#id_phone_carrier").val(data.phone_carrier);
                        $("#id_phone_carrier").trigger("change");
                        $("#id_phone_carrier").trigger("chosen:updated");

                        if (data.phone_verified) {
                            $($("#id_phone_verification_status").html('<i class="icon-ok bigger-110 green"></i> Verified'));
                        } else {
                            $($("#id_phone_verification_status").html(''));
                        }
                        $("#phone_verification_row").hide("fast");
                    }

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

        helium.clear_form_errors($(this).attr("id"));

        if ($("#id_old_password").val() !== '' || $("#id_new_password1").val() !== '' || $("#id_new_password2").val() !== '') {
            // If one is present, all three must be present
            var has_error = false;
            if ($("#id_old_password").val() === '') {
                helium.show_error("old_password", "This field is required.");

                has_error = true;
            }
            if ($("#id_new_password1").val() === '') {
                helium.show_error("new_password1", "This field is required.");

                has_error = true;
            }
            if ($("#id_new_password2").val() === '') {
                helium.show_error("new_password2", "This field is required.");

                has_error = true;
            }

            if (has_error) {
                $("#loading-account").spin(false);

                return false;
            }
        }

        $.ajax().always(function () {
            var form = $("#account-form"), data = form.serializeArray();

            for (var i = data.length - 1; i >= 0; --i) {
                if (data[i].name.indexOf('password') !== -1 && data[i].value == '') {
                    data.splice(i);
                }
            }

            $.ajax({
                async: false,
                context: form,
                data: data,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                type: 'PUT',
                url: '/api/auth/users/' + helium.USER_PREFS.id + '/',
                error: function (xhr) {
                    $.each(xhr.responseJSON, function (key, value) {
                        helium.show_error(key, value);
                    });

                    $("#loading-account").spin(false);
                },
                success: function (data) {
                    if (data.email_changing) {
                        self.email_pending(data.email_changing);
                    }

                    $("#loading-account").spin(false);
                }
            });
        });
    });

    this.refresh_feeds = function () {
        if (helium.USER_PREFS.settings.private_slug === null) {
            $("#enable-disable-feed").addClass("btn-success");
            $("#enable-disable-feed").removeClass("btn-warning");
            $("#enable-disable-feed").html('<i class="icon-check"></i>Enable Private Feeds');

            $("#private-feed-urls").html("Private feeds are not yet enabled. Enable using the button below.");
        } else {
            $("#enable-disable-feed").removeClass("btn-success");
            $("#enable-disable-feed").addClass("btn-warning");
            $("#enable-disable-feed").html('<i class="icon-check-minus"></i>Disable Private Feeds');

            var base_url = helium.SITE_URL + "feed/private/" + helium.USER_PREFS.settings.private_slug;

            $("#private-feed-urls").html("<strong>Events: </strong><a href=\"" + base_url + "\"/events.ics\">" + base_url + "/events.ics</a>" +
                "<br /><strong>Homework: </strong><a href=\"" + base_url + "\"/homework.ics\">" + base_url + "/homework.ics</a>");
        }
    };

    $("#enable-disable-feed").on("click", function () {
        $("#loading-feed").spin(helium.SMALL_LOADING_OPTS);

        if (helium.USER_PREFS.settings.private_slug === null) {
            $.ajax({
                async: false,
                type: 'PUT',
                url: '/api/feed/private/enable/',
                error: function () {
                    $("#status_feed").html('Sorry, an unknown error occurred while trying to enable feeds. Please <a href="/contact">contact support</a>').addClass("alert-warning").removeClass("hidden");

                    $("#loading-feed").spin(false);
                },
                success: function (data) {
                    helium.USER_PREFS.settings.private_slug = data.events_private_url.substr(14, data.events_private_url.lastIndexOf('/') - 14);

                    $("#loading-feed").spin(false);
                }
            });
        } else {
            $.ajax({
                async: false,
                type: 'PUT',
                url: '/api/feed/private/disable/',
                error: function () {
                    $("#status_feed").html('Sorry, an unknown error occurred while trying to enable feeds. Please <a href="/contact">contact support</a>').addClass("alert-warning").removeClass("hidden");

                    $("#loading-feed").spin(false);
                },
                success: function () {
                    helium.USER_PREFS.settings.private_slug = null;

                    $("#loading-feed").spin(false);
                }
            });
        }

        self.refresh_feeds();
    });

    $("#delete-account").on("click", function () {
        bootbox.dialog({
            title: "To permanently delete your Helium account <em>and all data you have stored in Helium</em>, confirm your password below.",
            message: '<input id="delete-account" name="delete-account" type="password" class="form-control" />',
            inputType: "password",
            closeButton: true,
            onEscape: true,
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
                            data: JSON.stringify(data),
                            type: 'DELETE',
                            url: '/api/auth/users/' + helium.USER_PREFS.id + '/',
                            error: function () {
                                $("#status_account").html('Sorry, an unknown error occurred while trying to delete your account. Please <a href="/contact">contact support</a>').addClass("alert-warning").removeClass("hidden");

                                $("#loading-account").spin(false);
                            },
                            success: function () {
                                $("#loading-account").spin(false);

                                Cookies.set("status_type", "warning", {path: "/"});
                                Cookies.set("status_msg", "Sorry to see you go! We've deleted all traces of your existence from Helium.", {path: "/"});

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

    helium.settings.populate_externalcalendars();

    $("#id_default_view").val(helium.USER_PREFS.settings.default_view);
    $("#id_week_starts_on").val(helium.USER_PREFS.settings.week_starts_on);
    $("#id_time_zone").val(helium.USER_PREFS.settings.time_zone);
    $("#id_time_zone").trigger("change");
    $("#id_time_zone").trigger("chosen:updated");
    $("#id_events_color").simplecolorpicker("selectColor", helium.USER_PREFS.settings.events_color);
    $("#id_default_reminder_type").val(helium.USER_PREFS.settings.default_reminder_type);
    $("#id_default_reminder_offset").val(helium.USER_PREFS.settings.default_reminder_offset);
    $("#id_default_reminder_offset_type").val(helium.USER_PREFS.settings.default_reminder_offset_type);
    $("#id_phone").val(helium.USER_PREFS.profile.phone);
    $("#id_phone_carrier").val(helium.USER_PREFS.profile.phone_carrier);
    $("#id_phone_carrier").trigger("change");
    $("#id_phone_carrier").trigger("chosen:updated");
    $("#id_username").val(helium.USER_PREFS.username);
    $("#id_email").val(helium.USER_PREFS.email);

    if (helium.USER_PREFS.email_changing === null) {
        ($("#id_email_verification_status").html('<i class="icon-ok bigger-110 green"></i> Verified'));
    } else {
        helium.settings.email_pending(helium.USER_PREFS.email_changing);
    }

    if ((helium.USER_PREFS.profile.phone_changing !== null && helium.USER_PREFS.profile.phone_changing !== '') ||
        (helium.USER_PREFS.profile.phone_carrier_changing !== null && helium.USER_PREFS.profile.phone_carrier_changing !== '')) {
        helium.settings.phone_pending(helium.USER_PREFS.profile.phone_changing);
    } else if (helium.USER_PREFS.profile.phone_verified) {
        ($("#id_phone_verification_status").html('<i class="icon-ok bigger-110 green"></i> Verified'));
    }

    helium.settings.refresh_feeds();
});