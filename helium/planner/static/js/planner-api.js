/**
 * Copyright (c) 2017 Helium Edu.
 *
 * JavaScript API for requests into server-side functionality for /planner pages.
 *
 * FIXME: This implementation is pretty crude compared to modern standards and will be completely overhauled in favor of a framework once the open source migration is completed.
 *
 * @author Alex Laird
 * @version 1.0.0
 */

/**
 * Create the Helium API persistence object.
 *
 * @constructor construct the HeliumPlannerAPI persistence object
 */
function HeliumPlannerAPI() {
    "use strict";

    this.GENERIC_ERROR_MESSAGE = "Oops, something went wrong while trying to communicate with the Helium servers. Try refreshing the page. If the error persists, <a href=\"/support\">contact support</a>.";

    this.course_groups_by_user_id = {};
    this.course_group = {};
    this.courses_around_date = {};
    this.courses_by_course_group_id = {};
    this.courses_by_user_id = {};
    this.course = {};
    this.material_group = {};
    this.materials_by_material_group_id = {};
    this.materials_by_course_id = {};
    this.material = {};
    this.category_names = null;
    this.categories_by_course_id = {};
    this.category = {};
    this.homework_by_course_id = {};
    this.homework = {};
    this.event = {};
    this.events_by_user_id = {};
    this.external_calendars_by_user_id = {};
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
            type: "POST",
            url: "/helium/update_user_details/" + user_id,
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Compile data for display on the /grades page for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the User ID with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.get_grades_by_user_id = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;

        return $.ajax({
            type: "POST",
            url: "/planner/grades_by_user_id/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Compile the CourseGroups for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the User ID with which to associate
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
                url: "/api/planner/coursegroups",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.course_groups_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.course_groups_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
                url: "/api/planner/coursegroups/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.course_group[id] = data;
                    callback(self.course_group[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            url: "/api/planner/coursegroups/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Compile all Courses that have a start/end date around the given date and pass the values to the given callback
     * function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param date the date to surround, must be in the format YYYY-MM-DD
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_courses_around_date = function (callback, date, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.courses_around_date.hasOwnProperty(date)) {
            ret_val = callback(self.courses_around_date[date]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/planner/courses_around_date/" + date,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_around_date[date] = data;
                    callback(self.courses_around_date[date]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
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
                url: "/api/planner/coursegroups/" + id + "/courses",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_by_course_group_id[id] = data;
                    callback(self.courses_by_course_group_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Courses for the given User Profile ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the User Profile with which to associate
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
                url: "/api/planner/courses",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.courses_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile all Courses (excluding those in hidden groups) for the given User Profile ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the User Profile with which to associate
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
                url: "/api/planner/courses",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.courses_by_user_id[helium.USER_PREFS.id] = data;
                    callback(self.courses_by_user_id[helium.USER_PREFS.id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.course[id] = data;
                    callback(self.course[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
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
                type: "POST",
                url: "/planner/material_group/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.material_group[id] = data;
                    callback(self.material_group[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
            url: "/planner/material_group/add",
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            type: "POST",
            url: "/planner/material_group/edit/" + id,
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            type: "POST",
            url: "/planner/material_group/delete/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
                type: "POST",
                url: "/planner/materials_by_course_id/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.materials_by_course_id[id] = data;
                    callback(self.materials_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Material for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Material
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_material = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.material.hasOwnProperty(id)) {
            ret_val = callback(self.material[id]);
        } else {
            ret_val = $.ajax({
                type: "POST",
                url: "/planner/material/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.material[id] = data;
                    callback(self.material[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
                type: "POST",
                url: "/planner/materials_by_material_group_id/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.materials_by_material_group_id[id] = data;
                    callback(self.materials_by_material_group_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new Material and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new Material
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_material = function (callback, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.materials_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/material/add",
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Edit the Material for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Material
     * @param data the array of values to update for the Material
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_material = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.material[id];
        self.materials_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/material/edit/" + id,
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Delete the Material for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Material
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_material = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.material[id];
        self.materials_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/material/delete/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
                type: "POST",
                url: "/planner/category_names",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.category_names = data;
                    callback(self.category_names);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + id + "/categories",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.categories_by_course_id[id] = data;
                    callback(self.categories_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
                url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/categories/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.category[id] = data;
                    callback(self.category[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
            url: "/api/planner/coursegroups/" + course_group_id + "/courses/" + course_id + "/categories/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Compile all Homework for the given Course ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Course with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_homework_by_course_id = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.homework_by_course_id.hasOwnProperty(id)) {
            ret_val = callback(self.homework_by_course_id[id]);
        } else {
            ret_val = $.ajax({
                type: "POST",
                url: "/planner/homework_by_course_id/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.homework_by_course_id[id] = data;
                    callback(self.homework_by_course_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Homework for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Homework
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_homework = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.homework.hasOwnProperty(id)) {
            ret_val = callback(self.homework[id]);
        } else {
            ret_val = $.ajax({
                type: "POST",
                url: "/planner/homework/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.homework[id] = data;
                    callback(self.homework[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Create a new Homework and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new Homework
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.add_homework = function (callback, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.homework_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/homework/add",
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Clone the given Homework and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new Homework
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.clone_homework = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        self.homework_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/homework/clone/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Edit the Homework for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Homework
     * @param data the array of values to update for the Homework
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_homework = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.homework[id];
        self.homework_by_course_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: "POST",
            url: "/planner/homework/edit/" + id,
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Delete the Homework for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Homework
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_homework = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.homework[id];
        self.homework_by_course_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/homework/delete/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Compile all Events for the given User ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the User with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_events_by_user_id = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.events_by_user_id.hasOwnProperty(id)) {
            ret_val = callback(self.events_by_user_id[id]);
        } else {
            ret_val = $.ajax({
                type: "POST",
                url: "/planner/events_by_user_id/" + id,
                async: async,
                dataType: "json",
                success: function (data) {
                    self.events_by_user_id[id] = data;
                    callback(self.events_by_user_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Compile the Event for the given ID and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Event
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_event = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.event.hasOwnProperty(id.substr(6))) {
            ret_val = callback(self.event[id.substr(6)]);
        } else {
            ret_val = $.ajax({
                type: "POST",
                url: "/planner/event/" + id.substr(6),
                async: async,
                dataType: "json",
                success: function (data) {
                    self.event[id] = data;
                    callback(self.event[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
            url: "/planner/event/add",
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Clone the given Event and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param data the array of values to set for the new Event
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.clone_event = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        self.events_by_user_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/event/clone/" + id.substr(6),
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Edit the Event for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Event
     * @param data the array of values to update for the Event
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_event = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.event[id.substr(6)];
        self.events_by_user_id = {};
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: "POST",
            url: "/planner/event/edit/" + id.substr(6),
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Delete the Event for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Event
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.delete_event = function (callback, id, async) {
        async = typeof async === "undefined" ? true : async;
        delete self.event[id];
        self.events_by_user_id = {};
        return $.ajax({
            type: "POST",
            url: "/planner/event/delete/" + id.substr(6),
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    /**
     * Compile all Calendar Sources for the given user and pass the values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the user with which to associate
     * @param async true if call should be async, false otherwise (default is true)
     * @param use_cache true if the call should attempt to used cache data, false if a database call should be made to refresh the cache (default to false)
     */
    this.get_external_calendars = function (callback, id, async, use_cache) {
        async = typeof async === "undefined" ? true : async;
        use_cache = typeof use_cache === "undefined" ? false : use_cache;
        var ret_val = null;

        if (use_cache && self.external_calendars_by_user_id.hasOwnProperty(id)) {
            ret_val = callback(self.external_calendars_by_user_id[id]);
        } else {
            ret_val = $.ajax({
                type: "GET",
                url: "/api/feed/externalcalendars",
                async: async,
                dataType: "json",
                success: function (data) {
                    self.external_calendars_by_user_id[id] = data;
                    callback(self.external_calendars_by_user_id[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
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
            ret_val = $.ajax({
                type: "POST",
                url: "/planner/reminders_by_calendar_item/" + (calendar_item_type === "0" ? id.substr(6) : id),
                data: {calendar_item_type: calendar_item_type},
                async: async,
                dataType: "json",
                success: function (data) {
                    self.reminders_by_calendar_item[id] = data;
                    callback(self.reminders_by_calendar_item[id]);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    callback([{
                        'err_msg': self.GENERIC_ERROR_MESSAGE,
                        'jqXHR': jqXHR,
                        'textStatus': textStatus,
                        'errorThrown': errorThrown
                    }]);
                }
            });
        }

        return ret_val;
    };

    /**
     * Edit the Reminder for the given ID and pass the returned values to the given callback function in JSON format.
     *
     * @param callback function to pass response data and call after completion
     * @param id the ID of the Reminder
     * @param data the array of values to update for the Category
     * @param async true if call should be async, false otherwise (default is true)
     */
    this.edit_reminder = function (callback, id, data, async) {
        async = typeof async === "undefined" ? true : async;
        self.reminders_by_calendar_item = {};
        return $.ajax({
            type: "POST",
            url: "/planner/reminder/edit/" + id,
            async: async,
            data: data,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
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
        return $.ajax({
            type: "POST",
            url: "/planner/attachments_by_calendar_item/" + (calendar_item_type === "0" ? id.substr(6) : id),
            async: async,
            data: {calendar_item_type: calendar_item_type},
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    this.enable_feed = function (callback, feed_type, id, async) {
        async = typeof async === "undefined" ? true : async;
        return $.ajax({
            type: "POST",
            url: "/planner/enable_feed/" + feed_type + "/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };

    this.disable_feed = function (callback, feed_type, id, async) {
        async = typeof async === "undefined" ? true : async;
        return $.ajax({
            type: "POST",
            url: "/planner/disable_feed/" + feed_type + "/" + id,
            async: async,
            dataType: "json",
            success: callback,
            error: function (jqXHR, textStatus, errorThrown) {
                callback([{
                    'err_msg': self.GENERIC_ERROR_MESSAGE,
                    'jqXHR': jqXHR,
                    'textStatus': textStatus,
                    'errorThrown': errorThrown
                }]);
            }
        });
    };
}

// Initialize HeliumPlannerAPI and give a reference to the Helium object
helium.planner_api = new HeliumPlannerAPI();