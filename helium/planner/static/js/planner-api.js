/**
 * Copyright (c) 2018 Helium Edu.
 *
 * JavaScript API for requests into server-side functionality for /planner pages.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.1
 */

/**
 * Create the Helium API persistence object.
 *
 * @constructor construct the HeliumPlannerAPI persistence object
 */
function HeliumPlannerAPI() {
    "use strict";

    this.GENERIC_ERROR_MESSAGE = "Oops, an unknown error has occurred. If the issue persists, <a href=\"/support\">contact support</a>.";

    this.course_groups_by_user_id = {};
    this.course_group = {};
    this.courses_by_course_group_id = {};
    this.courses_by_user_id = {};
    this.course = {};
    this.material_groups_by_user_id = {};
    this.material_group = {};
    this.materials_by_material_group_id = {};
    this.materials_by_course_id = {};
    this.material = {};
    this.category_names = null;
    this.categories_by_course_id = {};
    this.category = {};
    this.attachment = {};
    this.attachments_by_course_id = {};
    this.homework_by_user_id = {};
    this.homework_by_course_id = {};
    this.homework = {};
    this.event = {};
    this.events_by_user_id = {};
    this.external_calendars_by_user_id = {};
    this.external_calendar_feed = {};
    this.reminders_by_user_id = {};
    this.reminders_by_calendar_item = {};

    var self = this;

    /**
     * Clear all cache variables to force calls to get fresh data from the database.
     */
    this.clear_all_caches = function () {
        self.course_groups_by_user_id = {};
        self.course_group = {};
        self.courses_around_date = {};
        self.courses_by_course_group_id = {};
        self.courses_by_user_id = {};
        self.course = {};
        self.material_group = {};
        self.materials_by_material_group_id = {};
        self.materials_by_course_id = {};
        self.material = {};
        self.category_names = null;
        self.categories_by_course_id = {};
        self.category = {};
        self.homework_by_course_id = {};
        self.homework = {};
        self.event = {};
        self.events_by_user_id = {};
        self.external_calendars_by_user_id = {};
        self.reminders_by_calendar_item = {};
    };

    /**
     * Update user details.
     *
     * @param callback function to pass response data and call after completion
     * @param user_id the user ID to update
     * @param data the array of values to update for the user
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.update_user_details = function (callback, user_id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.course_groups_by_user_id = {};
        return $.ajax({
            type: "PUT",
            url: "/api/auth/users/" + helium.USER_PREFS.id + "/settings/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile data for display on the /grades page for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.get_grades = function (callback, async) {
        async = typeof async === "undefined" ? true : async;

        return $.ajax({
            type: "GET",
            url: "/api/planner/grades/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile the CourseGroups for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_course_groups = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.course_groups_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.course_groups_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.course_groups_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.course_groups_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the CourseGroup for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the CourseGroup
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_course_group = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.course_group.hasOwnProperty(id)) {
            ret_val = callback(self.course_group[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.course_group[id] = data;
                    callback(self.course_group[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new CourseGroup and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new CourseGroup
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_course_group = function (callback, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.course_groups_by_user_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/coursegroups/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the CourseGroup for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the CourseGroup
     * @param data the array of values to update for the CourseGroup
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_course_group = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.course_group[id];
        self.course_groups_by_user_id = {};
        return $.ajax({
            type: "PUT",
            url: "/api/planner/coursegroups/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the CourseGroup for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the CourseGroup
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_course_group = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.course_group[id];
        self.course_groups_by_user_id = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/coursegroups/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Courses for the given CourseGroup ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the CourseGroup with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_courses_by_course_group_id = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.courses_by_course_group_id.hasOwnProperty(id)) {
            ret_val = callback(self.courses_by_course_group_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + id + "/courses/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_by_course_group_id[id] = data;
                    callback(self.courses_by_course_group_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Courses for the given User Profile ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_all_courses_by_user_id = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.courses_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.courses_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/courses/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.courses_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Courses (excluding those in hidden groups) for the given User Profile ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_courses = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.courses_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.courses_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/courses/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.courses_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Course for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param id the ID of the Course
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_course = function (callback, course_group_id, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.course.hasOwnProperty(id)) {
            ret_val = callback(self.course[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.course[id] = data;
                    callback(self.course[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new Course and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param data the array of values to set for the new Course
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_course = function (callback, course_group_id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.courses_around_date = {};
        self.courses_by_course_group_id = {};
        self.courses_by_user_id = {};
        self.category_names = null;
        self.categories_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Course for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param id the ID of the Course
     * @param data the array of values to update for the Course
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_course = function (callback, course_group_id, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.course[id];
        self.courses_around_date = {};
        self.courses_by_course_group_id = {};
        self.courses_by_user_id = {};
        self.category_names = null;
        self.categories_by_course_id = {};
        return $.ajax({
            type: "PUT",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0 && jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]].length > 0) {
                    data['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the Course for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param id the ID of the Course
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_course = function (callback, course_group_id, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.course[id];
        self.courses_around_date = {};
        self.courses_by_course_group_id = {};
        self.courses_by_user_id = {};
        self.category_names = null;
        self.categories_by_course_id = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile the MaterialGroups for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_material_groups = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.material_groups_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.material_groups_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/materialgroups/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.material_groups_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.material_groups_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the MaterialGroup for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the MaterialGroup
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_material_group = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.material_group.hasOwnProperty(id)) {
            ret_val = callback(self.material_group[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/materialgroups/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.material_group[id] = data;
                    callback(self.material_group[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new MaterialGroup and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new MaterialGroup
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_material_group = function (callback, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.material_group = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/materialgroups/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the MaterialGroup for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the MaterialGroup
     * @param data the array of values to update for the CourseGroup
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_material_group = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.material_group[id];
        self.material_group = {};
        return $.ajax({
            type: "PUT",
            url: "/api/planner/materialgroups/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the MaterialGroup for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the MaterialGroup
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_material_group = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.material_group[id];
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/materialgroups/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Materials for the given Course ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Course with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_materials_by_course_id = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.materials_by_course_id.hasOwnProperty(id)) {
            ret_val = callback(self.materials_by_course_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/materials/?course=" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.materials_by_course_id[id] = data;
                    callback(self.materials_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Material for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param material_group_id the ID of the MaterialGroup
     * @param id the ID of the Material
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_material = function (callback, material_group_id, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.material.hasOwnProperty(id)) {
            ret_val = callback(self.material[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/materialgroups/" + material_group_id + "/materials/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.material[id] = data;
                    callback(self.material[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Material for the given material group ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the MaterialGroup
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_materials_by_material_group_id = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.materials_by_material_group_id.hasOwnProperty(id)) {
            ret_val = callback(self.materials_by_material_group_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/materialgroups/" + id + "/materials/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.materials_by_material_group_id[id] = data;
                    callback(self.materials_by_material_group_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new Material and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param material_group_id the ID of the MaterialGroup
     * @param data the array of values to set for the new Material
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_material = function (callback, material_group_id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.materials_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/materialgroups/" + material_group_id + "/materials/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Material for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param material_group_id the ID of the MaterialGroup
     * @param id the ID of the Material
     * @param data the array of values to update for the Material
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_material = function (callback, material_group_id, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.material[id];
        self.materials_by_course_id = {};
        return $.ajax({
            type: "PUT",
            url: "/api/planner/materialgroups/" + material_group_id + "/materials/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the Material for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param material_group_id the ID of the MaterialGroup
     * @param id the ID of the Material
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_material = function (callback, material_group_id, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.material[id];
        self.materials_by_course_id = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/materialgroups/" + material_group_id + "/materials/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Categories names and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_category_names = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.category_names !== null) {
            ret_val = callback(self.category_names);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/categories/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.category_names = [];
                    $.each(data, function (index, category) {
                        self.category_names.push(category);
                    });
                    callback(self.category_names);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Categories for the given Course ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup with which to associate
     * @param id the ID of the Course with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_categories_by_course_id = function (callback, course_group_id, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.categories_by_course_id.hasOwnProperty(id)) {
            ret_val = callback(self.categories_by_course_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id + "/categories/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.categories_by_course_id[id] = data;
                    callback(self.categories_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Category for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param id the ID of the Category
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_category = function (callback, course_group_id, course_id, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.category.hasOwnProperty(id)) {
            ret_val = callback(self.category[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/categories/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.category[id] = data;
                    callback(self.category[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create new Categories and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param data the array of values to set for the new Category
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_category = function (callback, course_group_id, course_id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.category_names = null;
        self.categories_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/categories/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Category for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param id the ID of the Category
     * @param data the array of values to update for the Category
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_category = function (callback, course_group_id, course_id, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.category[id];
        self.category_names = null;
        self.categories_by_course_id = {};
        return $.ajax({
            type: "PUT",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/categories/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the Category for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param id the ID of the Category
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_category = function (callback, course_group_id, course_id, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.category[id];
        self.category_names = null;
        self.categories_by_course_id = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/categories/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Attachments for the given Course ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Course with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_attachments_by_course_id = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.attachments_by_course_id.hasOwnProperty(id)) {
            ret_val = callback(self.attachments_by_course_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/attachments/?course=" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.categories_by_course_id[id] = data;
                    callback(self.categories_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Delete the Attachment for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Attachment
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_attachment = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.attachment[id];
        self.attachments_by_course_id = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/attachments/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Homework for the given Course ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_homework_by_user = function (callback, async, use_cache, start, end) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.homework_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.homework_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/homework/" + (start !== "undefined" ? "?start__gte=" + start : "") + (end !== "undefined" ? "&end__lt=" + end : ""),
                async: async,
                dataType: "json",
                success: function (data) {
                    self.homework_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.homework_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Homework for the given Course ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup with which to associate
     * @param id the ID of the Course with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_homework_by_course_id = function (callback, course_group_id, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.homework_by_course_id.hasOwnProperty(id)) {
            ret_val = callback(self.homework_by_course_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id + "/homework/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.homework_by_course_id[id] = data;
                    callback(self.homework_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Homework for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param id the ID of the Homework
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_homework = function (callback, course_group_id, course_id, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.homework.hasOwnProperty(id)) {
            ret_val = callback(self.homework[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/homework/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.homework[id] = data;
                    callback(self.homework[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    this.get_homework_by_id = function (callback, id, use_cache) {
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.homework.hasOwnProperty(id)) {
            ret_val = callback(self.homework[id]);
        } else {
            ret_val = this.get_homework_by_user(function (data) {
                $.each(data, function (index, homework) {
                    if (homework.id == id) {
                        self.homework[id] = homework;
                        callback(self.homework[id]);
                    }
                });
            }, false, use_cache);
        }

        return ret_val;
    };

    /**
     * Create a new Homework and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param data the array of values to set for the new Homework
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_homework = function (callback, course_group_id, course_id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.homework_by_course_id = {};
        self.homework_by_user_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/homework/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Homework for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param id the ID of the Homework
     * @param data the array of values to update for the Homework
     * @param async true if call should be async, false otherwise (default is true)
     * @param patch true if call should be patch instead of put, false otherwise (default is false)
     */
    this.edit_homework = function (callback, course_group_id, course_id, id, data, async, patch) {
        async = typeof async === "undefined" ? true : async;
        patch = typeof patch === "undefined" ? false : patch;
        delete self.homework[id];
        self.homework_by_course_id = {};
        self.homework_by_user_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: patch ? "PATCH" : "PUT",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/homework/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the Homework for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param course_group_id the ID of the CourseGroup
     * @param course_id the ID of the Course
     * @param id the ID of the Homework
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_homework = function (callback, course_group_id, course_id, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.homework[id];
        self.homework_by_course_id = {};
        self.homework_by_user_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/homework/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Events for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_events = function (callback, async, use_cache, start, end) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.events_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.events_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/events/" + (start !== "undefined" ? "?start__gte=" + start : "") + (end !== "undefined" ? "&end__lt=" + end : ""),
                async: async,
                dataType: "json",
                success: function (data) {
                    self.events_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.events_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Event for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Event.
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_event = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (id.lastIndexOf("event_", 0) === 0) {
            id = id.substr(6);
        }

        if (use_cache && self.event.hasOwnProperty(id)) {
            ret_val = callback(self.event[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/events/" + id + "/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.event[id] = data;
                    callback(self.event[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new Event and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new Event
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_event = function (callback, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.events_by_user_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/events/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Event for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Event.
     * @param data the array of values to update for the Event
     * @param async true if call should be async, false otherwise (default is true)
     * @param patch true if call should be patch instead of put, false otherwise (default is false)
     */
    this.edit_event = function (callback, id, data, async, patch) {
        async = typeof async === "undefined" ? true : async;
        patch = typeof patch === "undefined" ? true : patch;

        if (id.lastIndexOf("event_", 0) === 0) {
            id = id.substr(6);
        }

        delete self.event[id];
        self.events_by_user_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: patch ? "PATCH" : "PUT",
            url: "/api/planner/events/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Delete the Event for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Event.
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_event = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;

        if (id.lastIndexOf("event_", 0) === 0) {
            id = id.substr(6);
        }

        delete self.event[id];
        self.events_by_user_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/events/" + id + "/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Compile all Calendar Sources for the given user and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_external_calendars = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.external_calendars_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.external_calendars_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/feed/externalcalendars/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.external_calendars_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.external_calendars_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Events for the given External Calendar source and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id The ID of the ExternalCalendar.
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_external_calendar_feed = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.external_calendar_feed.hasOwnProperty(id)) {
            ret_val = callback(self.external_calendar_feed[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/feed/externalcalendars/" + id + "/externalevents/",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.external_calendar_feed[id] = data;
                    callback(self.external_calendar_feed[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Reminders for the authenticated user.
     *
     * @param callback function to pass response data and call after completion
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_reminders = function (callback, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.reminders_by_user_id.hasOwnProperty(helium.USER_PREFS.id)) {
            ret_val = callback(self.reminders_by_user_id[helium.USER_PREFS.id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/reminders/?sent=false&type=0&start_of_range__lte=" + moment().toISOString(),
                async: async,
                dataType: "json",
                success: function (data) {
                    self.reminders_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.reminders_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Reminders for the given calendar item (Homework or Event) and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the user with which to associate
     * @param calendar_item_type true if the item is an event, false otherwise
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_reminders_by_calendar_item = function (callback, id, calendar_item_type, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.reminders_by_calendar_item.hasOwnProperty(id)) {
            ret_val = callback(self.reminders_by_calendar_item[id]);
        } else {
            var query = calendar_item_type === "0" ? "event=" + id : "homework=" + id;

            ret_val = $.ajax({
                type: "GET",
                url: "/api/planner/reminders/?" + query,
                data: {calendar_item_type: calendar_item_type},
                async: async,
                dataType: "json",
                success: function (data) {
                    self.reminders_by_calendar_item[id] = data;
                    callback(self.reminders_by_calendar_item[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var data = [{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }];
                    if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                        var name = Object.keys(jqXHR.responseJSON)[0];
                        if (jqXHR.responseJSON[name].length > 0) {
                            data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                        }
                    }
                    callback(data);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new Reminder and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new Reminder
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_reminder = function (callback, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.events_by_user_id = {};
        return $.ajax({
            type: "POST",
            url: "/api/planner/reminders/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Reminder for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Reminder
     * @param data the array of values to update for the Category
     * @param async true if call should be async, false otherwise (default is true)
     * @param patch true if call should be patch instead of put, false otherwise (default is false)
     */
    this.edit_reminder = function (callback, id, data, async, patch) {
        async = typeof async === "undefined" ? true : async;
        patch = typeof patch === "undefined" ? false : patch;
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: patch ? "PATCH" : "PUT",
            url: "/api/planner/reminders/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Edit the Reminder for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Reminder
     * @param data the array of values to update for the Category
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_reminder = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.reminders_by_user_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: "DELETE",
            url: "/api/planner/reminders/" + id + "/",
            async: async,
            data: JSON.stringify(data),
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    /**
     * Get the attachments for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Attachment
     * @param calendar_item_type true if the item is an event, false otherwise
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.get_attachments_for_calendar_item = function (callback, id, calendar_item_type, async) {
        async = typeof async === "undefined" ? true : async;
        var query = calendar_item_type === "0" ? "event=" + id : "homework=" + id;
        return $.ajax({
            type: "GET",
            url: "/api/planner/attachments/?" + query,
            async: async,
            data: {calendar_item_type: calendar_item_type},
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    this.enable_feed = function (callback, feed_type, id, async) {
        async = typeof async === "undefined" ? true : async;
        return $.ajax({
            type: "PUT",
            url: "/api/feeds/enable-external/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };

    this.disable_feed = function (callback, feed_type, id, async) {
        async = typeof async === "undefined" ? true : async;
        return $.ajax({
            type: "PUT",
            url: "/api/feeds/disable-external/",
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                var data = [{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }];
                if (jqXHR.hasOwnProperty('responseJSON') && Object.keys(jqXHR.responseJSON).length > 0) {
                    var name = Object.keys(jqXHR.responseJSON)[0];
                    if (jqXHR.responseJSON[name].length > 0) {
                        data[0]['err_msg'] = jqXHR.responseJSON[Object.keys(jqXHR.responseJSON)[0]][0];
                    }
                }
                callback(data);
            }
        });
    };
}

// Initialize HeliumPlannerAPI and give a reference to the Helium object
helium.planner_api = new HeliumPlannerAPI();

if (typeof USER_ID !== 'undefined') {
    helium.planner_api.get_reminders(function (data) {
        helium.process_reminders(data);
    });

    window.setInterval(function () {
        helium.planner_api.get_reminders(function (data) {
            helium.process_reminders(data);
        });
    }, 60000);
}