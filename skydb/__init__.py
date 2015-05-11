import os
from os import listdir
from os.path import abspath, isdir, join
import fnmatch
import datetime

import numpy as np

from envmap import EnvironmentMap
from hdrtools import sunutils
from tonemapping import reinhard2002, gamma


class SkyDB:
    def __init__(self, path):
        """Creates a SkyDB.
        The path should contain folders named by YYYYMMDD (ie. 20130619 for June 19th 2013).
        These folders should contain folders named by HHMMSS (ie. 102639 for 10h26 39s).
        Inside these folders should a file named envmap.exr be located.
        """
        p = abspath(path)
        self.intervals_dates = [join(p, f) for f in listdir(p) if isdir(join(p, f))]
        self.intervals = list(map(SkyInterval, self.intervals_dates))


class SkyInterval:
    def __init__(self, path):
        """Represent an interval, usually a day.
        The path should contain folders named by HHMMSS (ie. 102639 for 10h26 39s).
        """
        self.path =  path
        matches = []
        for root, dirnames, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, 'envmap.exr'):
                matches.append(join(root, filename))

        self.probes = list(map(SkyProbe, matches))
        self.reftimes = [x.datetime for x in self.probes]

        if len(self.probes) > 0:
            self.sun_visibility = sum(1 for x in self.probes if x.sun_visible) / len(self.probes)
        else:
            self.sun_visibility = 0

    @property
    def date(self):
        """
        :returns: datetime.date object
        """
        date = os.path.normpath(self.path).split(os.sep)[-1]
        infos = {
            "day": int(date[-2:]),
            "month": int(date[4:6]),
            "year": int(date[:4]),
        }
        return datetime.date(**infos)

    def closestProbe(self, hours, minutes=0, seconds=0):
        """
        Return the SkyProbe object closest to the requested time.
        TODO : check for day change (if we ask for 6:00 AM and the probe sequence
            only begins at 7:00 PM and ends at 9:00 PM, then 9:00 PM is actually
            closer than 7:00 PM and will be wrongly selected; not a big deal but...)
        """
        cmpdate = datetime.datetime(year=1, month=1, day=1, hour=hours, minute=minutes, second=seconds)
        idx = np.argmin([np.abs((cmpdate - t).total_seconds()) for t in self.reftimes])
        return self.probes[idx]


class SkyProbe:
    def __init__(self, path, format_='angular'):
        """Represent an environment map among an interval."""
        self.path = path
        self.format_ = format_

    @property
    def sun_visible(self):
        """
        :returns: boolean, True if the sun is visible, False otherwise.
        """
        envmap = EnvironmentMap(self.path, self.format_)
        return envmap.data.max() > 5000

    @property
    def mean_light_vector(self):
        """Mean light vector of the environment map.
        :returns: (elevation, azimuth)
        """
        raise NotImplementedError()

    @property
    def datetime(self):
        """Datetime of the capture.
        :returns: datetime object.
        """
        time_ = os.path.normpath(self.path).split(os.sep)[-2]
        date = os.path.normpath(self.path).split(os.sep)[-3]
        infos = {
            "second": int(time_[-2:]),
            "minute": int(time_[2:4]),
            "hour": int(time_[:2]),
            "day": int(date[-2:]),
            "month": int(date[4:6]),
            "year": int(date[:4]),
        }
        return datetime.datetime(**infos)

    @property
    def environment_map(self):
        """
        :returns: EnvironmentMap object.
        """
        return EnvironmentMap(self.path, self.format_)

    @property
    def sun_position(self):
        """
        :returns: (elevation, azimuth)
        """
        envmap = EnvironmentMap(self.path, self.format_)
        return sunutils.sunPosFromEnvmap(envmap)
