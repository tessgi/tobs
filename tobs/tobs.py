from __future__ import absolute_import

import argparse
from . import Highlight
from . import logger

from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.simbad import Simbad
from astropy.time import Time
from scipy.interpolate import interp1d
import numpy as np

import sys
import warnings


class Observable(object):

    def __init__(self, name):
        self.validate_name(name)
        self.name = name

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            result_table = Simbad.query_object(name)

        if result_table is None:
            logger.error("Target name failed to resolve, please check")
            sys.exit(1)

        self.ra_sex = result_table['RA'][0]
        self.dec_sex = result_table['DEC'][0]
        self.name = result_table['MAIN_ID'][0]

        self.skobj = SkyCoord(ra=self.ra_sex,
                              dec=self.dec_sex,
                              unit=(u.hourangle, u.deg),
                              frame='icrs')

    def get_hemisphere(self):
        lon_deg, lat_deg = self.get_ecliptic()
        if lat_deg < -5.5:
            return 'south'
        elif lat_deg > 5.5:
            return 'north'
        else:
            return False

    def get_hemisphererange(self):
        if self.get_hemisphere() is False:
            return None
        elif self.get_hemisphere() == 'south':
            times = ['2018-06-18T00:00:00', '2019-06-18T00:00:00']
            return Time(times, format='isot', scale='utc')
        elif self.get_hemisphere() == 'north':
            times = ['2019-06-18T00:00:00', '2020-06-18T00:00:00']
            return Time(times, format='isot', scale='utc')

    def get_antisolarlon(self, date):
        """
        from http://aa.usno.navy.mil/faq/docs/SunApprox.php
        """
        D = date.jd - 2451545.0
        g = 357.529 + 0.98560028 * D
        q = 280.459 + 0.98564736 * D
        L = q + 1.915 * np.sin(np.radians(g)) + 0.020 * \
            np.sin(np.radians(2 * g))
        return ((L + 180) % 360)

    def get_antisolardate(self):
        """
        expects and returns date as a datetime object
        """
        timerange = self.get_hemisphererange()
        if timerange is None:
            return None
        t = Time(timerange, format='isot', scale='utc')
        dt = t[1] - t[0]
        times = t[0] + dt * np.linspace(0., 1., 365 * 24 + 1)
        f = interp1d(self.get_antisolarlon(times), times.jd, kind='nearest')
        antisolardate = Time(f(self.get_ecliptic()[0]), format='jd',
                             out_subfmt='date_hm')
        return antisolardate

    def validate_name(self, name):
        pass

    def get_ecliptic(self):
        lon_deg = self.skobj.barycentrictrueecliptic.lon.value
        lat_deg = self.skobj.barycentrictrueecliptic.lat.value
        return lon_deg, lat_deg

    def get_galactic(self):
        l_deg = self.skobj.galactic.l.value
        b_deg = self.skobj.galactic.b.value
        return l_deg, b_deg

    def get_icrs(self):
        ra_deg = self.skobj.icrs.ra.value
        dec_deg = self.skobj.icrs.dec.value
        return ra_deg, dec_deg


def tobs(args=None):
    """
    exposes tobs to the command line
    """
    if args is None:
        parser = argparse.ArgumentParser(
            description="When might a star be observed by TESS")
        parser.add_argument('name', nargs='+',
                            help="Name of the target")
        args = parser.parse_args(args)
        args.name = ' '.join(args.name)
        args = vars(args)
    name = args['name']

    _output = print_results(name=name)


def print_results(ra=None, dec=None, name=None, sex=False):
    if sex:
        coords = Observable(ra, dec)
    elif name is not None:
        obs = Observable(name)
        print()
        print(Highlight.PURPLE +
              'Resolved name as {}'.format(obs.name.decode('utf-8')) +
              Highlight.END)
    else:
        coords = Coordinates(ra, dec)

    print()
    antisolardateobj = obs.get_antisolardate()

    if antisolardateobj is None:
        print(Highlight.CYAN +
          "Ecliptic target not observed by TESS" +
          Highlight.END)

    else:

        antisolar = antisolardateobj.iso
        earliest = (antisolardateobj - 28 * u.day).iso
        latest = (antisolardateobj + 28 * u.day).iso

        if (antisolardateobj - 28 * u.day).jd < 2458287.5:
            earliest = Time(2458287.5, format='jd')
     
        print(Highlight.CYAN +
              "antisolar date   = {}".format(antisolar) +
              Highlight.END)
        print(Highlight.RED +
              "earliest date    = {}".format(earliest) +
              Highlight.END)
        print(Highlight.BLUE +
              "latest date      = {}".format(latest) +
              Highlight.END)

        if np.abs(obs.get_ecliptic()[1]) > 30:
            print()
            print(Highlight.PURPLE +
                  'This object might be observed observed in multiple sectors\n' +
                  'It has eclat {:.4}. The dates here are lower limits.\n'.format(
                      obs.get_ecliptic()[1]) +
                  Highlight.END)

    print()
