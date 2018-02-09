# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-02-09 17:34
from __future__ import unicode_literals

import datetime

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def migrate_course_schedules(apps, schema_editor):
    Course = apps.get_model('planner', 'Course')
    CourseSchedule = apps.get_model('planner', 'CourseSchedule')
    for course in Course.objects.iterator():
        if course.days_of_week != '0000000':
            CourseSchedule.objects.create(days_of_week=course.days_of_week,
                                          sun_start_time=course.sun_start_time, sun_end_time=course.sun_end_time,
                                          mon_start_time=course.mon_start_time, mon_end_time=course.mon_end_time,
                                          tue_start_time=course.tue_start_time, tue_end_time=course.tue_end_time,
                                          wed_start_time=course.wed_start_time, wed_end_time=course.wed_end_time,
                                          thu_start_time=course.thu_start_time, thu_end_time=course.thu_end_time,
                                          fri_start_time=course.fri_start_time, fri_end_time=course.fri_end_time,
                                          sat_start_time=course.sat_start_time, sat_end_time=course.sat_end_time,
                                          course=course)
        if course.days_of_week_alt != '0000000':
            CourseSchedule.objects.create(days_of_week=course.days_of_week_alt,
                                          sun_start_time=course.sun_start_time_alt,
                                          sun_end_time=course.sun_end_time_alt,
                                          mon_start_time=course.mon_start_time_alt,
                                          mon_end_time=course.mon_end_time_alt,
                                          tue_start_time=course.tue_start_time_alt,
                                          tue_end_time=course.tue_end_time_alt,
                                          wed_start_time=course.wed_start_time_alt,
                                          wed_end_time=course.wed_end_time_alt,
                                          thu_start_time=course.thu_start_time_alt,
                                          thu_end_time=course.thu_end_time_alt,
                                          fri_start_time=course.fri_start_time_alt,
                                          fri_end_time=course.fri_end_time_alt,
                                          sat_start_time=course.sat_start_time_alt,
                                          sat_end_time=course.sat_end_time_alt,
                                          course=course)


class Migration(migrations.Migration):
    dependencies = [
        ('planner', '0004_auto_20180202_2232'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseSchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('days_of_week', models.CharField(default=b'0000000',
                                                  help_text=b'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).',
                                                  max_length=7, validators=[
                        django.core.validators.RegexValidator(b'^[0-1]+$',
                                                              b'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).',
                                                              b'invalid'), django.core.validators.MinLengthValidator(7,
                                                                                                                     b'Seven booleans (0 or 1) indicating which days of the week the course is on (week starts on Sunday).')])),
                ('sun_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('sun_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('mon_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('mon_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('tue_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('tue_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('wed_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('wed_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('thu_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('thu_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('fri_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('fri_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('sat_start_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
                ('sat_end_time', models.TimeField(default=datetime.time(12, 0), help_text=b'An ISO-8601 time.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='courseschedule',
            name='course',
            field=models.ForeignKey(help_text=b'The course with which to associate.',
                                    on_delete=django.db.models.deletion.CASCADE, related_name='schedules',
                                    to='planner.Course'),
        ),
        migrations.RunPython(migrate_course_schedules),
        migrations.RemoveField(
            model_name='course',
            name='days_of_week',
        ),
        migrations.RemoveField(
            model_name='course',
            name='days_of_week_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='fri_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='fri_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='fri_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='fri_start_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='mon_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='mon_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='mon_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='mon_start_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='private_slug',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sat_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sat_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sat_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sat_start_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sun_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sun_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sun_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='sun_start_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='thu_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='thu_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='thu_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='thu_start_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='tue_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='tue_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='tue_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='tue_start_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='wed_end_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='wed_end_time_alt',
        ),
        migrations.RemoveField(
            model_name='course',
            name='wed_start_time',
        ),
        migrations.RemoveField(
            model_name='course',
            name='wed_start_time_alt',
        ),
    ]
