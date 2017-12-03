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

    this.external_calendar_id = -1;

    var self = this;

    this.delete_source = function () {
        var row = $(this).parent().parent().parent();
        row.hide("fast", function () {
            $(this).remove();
            if ($("#sources-table-body").children().length === 1) {
                $("#no-sources").show();
            }
        });
    };

    $("#create-calendar-source").on("click", function () {
        self.external_calendar_id = self.external_calendar_id + 1;

        var div = $("#sources-table-body").append("<tr id=\"source-" + self.external_calendar_id + "-unsaved\"><td><a class=\"cursor-hover\" id=\"source-" + self.external_calendar_id + "-unsaved-title\">" + "New Sources" + "</td><td class=\"hidden-480\"><a class=\"cursor-hover\" id=\"source-" + self.external_calendar_id + "-unsaved-url\">" + "http://www.externalcalendar.com/feed" + "</a></td><td><input id=\"source-" + self.external_calendar_id + "-unsaved-enabled\" type=\"checkbox\" class=\"ace\" /><span class=\"lbl\" /></td><td><select id=\"source-" + self.external_calendar_id + "-unsaved-color-picker\" class=\"hide\">" + $("#allowed-colors").html() + "</select></td><td><div class=\"btn-group\"><button type=\"button\" class=\"btn btn-xs btn-danger\" id=\"delete-source-" + self.external_calendar_id + "-unsaved\"><i class=\"icon-trash bigger-120\"></i></button></div></td></tr>"), color_picker = div.find("#source-" + self.external_calendar_id + "-unsaved-color-picker").simplecolorpicker({
            picker: true,
            theme: "glyphicons"
        });
        color_picker.simplecolorpicker("selectColor", $($("#allowed-colors option")[Math.floor(Math.random() * $("#allowed-colors option").length)]).val());
        div.find("#source-" + self.external_calendar_id + "-unsaved-title").editable({
            type: "text",
            tpl: '<input type="text" maxlength="255">'
        });
        div.find("#source-" + self.external_calendar_id + "-unsaved-url").editable({
            type: "url",
            tpl: '<input type="url" maxlength="255">'
        });
        div.find("#delete-source-" + self.external_calendar_id + "-unsaved").on("click", self.delete_source);

        if ($("#sources-table-body").children().length === 2) {
            $("#no-sources").hide();
        }
    });

    $("[id^='delete-source-']").on("click", self.delete_source);

    $("#preferences-form").submit(function (e) {
        // Prevent default submit
        e.preventDefault();
        e.returnValue = false;

        $("#loading-calendar-sources").spin(helium.SMALL_LOADING_OPTS);

        $.ajax().always(function () {
            var form = $("#preferences-form"), data = form.serializeArray(), dom_id, id, unsaved_string;

            $.each(form.find("tr[id^='source-']"), function () {
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
                data.push({
                    name: dom_id, value: JSON.stringify({
                        title: form.find("#source-" + id + unsaved_string + "-title").html(),
                        url: form.find("#source-" + id + unsaved_string + "-url").html(),
                        color: form.find("#source-" + id + unsaved_string + "-color-picker").val(),
                        shown_on_calendar: form.find("#source-" + id + unsaved_string + "-enabled").is(":checked")
                    })
                });
            });
            $.ajax({
                async: false,
                context: form,
                data: data,
                type: form.attr("method"),
                url: form.attr("action"),
                error: function () {
                    $("#loading-calendar-sources").spin(false);

                    $("#settings-tab-1 > .page-header").after("<div id='preferences-status-div' class='alert alert-warning'>" + "Oops, an unknown error occurred when we tried to save the changes to your external calendars." + "</div>");
                },
                success: function () {
                    // Prevent the default submit action
                    this.off("submit");
                    // And submit the rest of the form manually
                    this.submit();
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
                        var password = $("input[name='delete-account']").val();
                        $("#account-settings-form").append($("<input>").attr("type", "hidden").attr("name", "delete-account").val(password));
                        $("#account-settings-form").submit();
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

    var id;

    $("#loading-calendar-sources").spin(false);

    // After a post, we want to remember which settings tab was being viewed
    $("a[data-toggle='tab']").on("shown.bs.tab", function (event) {
        $.cookie("settings_tab", $(event.target).attr("href"), {path: "/"});
    });

    $("#id_phone_carrier").chosen({width: "100%", search_contains: true, no_results_text: "No carriers match"});
    $("#id_time_zone").chosen({width: "100%", search_contains: true, no_results_text: "No time zones match"});
    $("#id_events_color").simplecolorpicker({picker: true, theme: "glyphicons"});

    $.each($("[id^='source-']"), function () {
        id = $(this).attr("id");
        if (id.indexOf("color-picker") !== -1) {
            id = id.split("-");
            id = id[id.length - 3];
            $(this).append($("#allowed-colors").html()).simplecolorpicker({picker: true, theme: "glyphicons"});
            $(this).simplecolorpicker("selectColor", $("#source-" + id + "-color").html());
        } else if (id.indexOf("title") !== -1 || id.indexOf("url") !== -1) {
            $(this).editable({
                type: "text",
                tpl: '<input type="text" maxlength="255">'
            });
        }
    });

    if ($("#sources-table-body").children().length === 1) {
        $("#no-sources").show();
    }

    if ($(".calendar-sources-help").length > 0) {
        $(".calendar-sources-help").popover({html: true}).data("bs.popover").tip().css("z-index", 1060);
        $(".calendar-sources-help").on("click", function () {
            window.open("https://support.google.com/calendar/answer/37648?hl=en");
        });
    }
});