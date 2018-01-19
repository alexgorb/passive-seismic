import pandas as pd
from obspy import UTCDateTime
from obspy.core.event import Event, Catalog, Origin, Comment, Pick
from obspy.core.event import CreationInfo
from obspy import read_events
from obspy.geodetics import locations2degrees
from inventory.parse_inventory import read_stations, sc3_inventory
from iloc_rstt.config import event_file, max_station_dist

stations = pd.read_csv(sc3_inventory)
stations_dict = read_stations(sc3_inventory)
DELTA = 'delta'  # distance in degrees between stations and source
STATION_COLS = ['station_code', 'latitude', 'longitude',
                'elevation', 'network_code']
PHASEHINT = 'phase_hint'


class ILocEvent:
    """
    Just a convenience class for event enhancement using iLoc
    """
    def __init__(self, event):
        self.old_origin = event.preferred_origin() or \
            event.origins[0]  # best guess origin
        self.event = event
        self.iloc_origin = None
        self.all_stations = None
        self.picks = event.picks
        self.magnitudes = event.magnitudes
        self.amplitudes = event.amplitudes
        self.station_magnitudes = event.station_magnitudes
        self.resource_id = event.resource_id
        self.event_descriptions = event.event_descriptions
        self.comments = event.comments
        self.creation_info = event.creation_info
        self.origins = event.origins
        self.focal_mechanisms = event.focal_mechanisms
        self.preferred_origin_id = self.old_origin.resource_id

    def __call__(self, *args, **kwargs):
        self.add_picks()
        return self

    def add_picks(self):
        if self.all_stations is None:
            self.all_stations = self.add_stations()
        return self.all_stations
        # mseed = self._get_miniseed()

    def add_magnitudes(self):
        return

    def _get_miniseed(self):
        # can make system call to seiscomp3 based on stations and event time
        # return mseed
        pass

    def add_origin(self):
        """
        Return the origin found by iLoc
        """
        if self.iloc_origin is None:
            # run iloc and return iloc determined origin
            return self.origins.append(Origin())
        else:
            return self.origins

    def add_stations(self, max_station_dist=max_station_dist):
        """
        :param max_station_dist: percentage distance to scan for extra stations

        Distance is calculated as percentage of the farthest station from the
        original preferred origin. A value of 100 implies an euclidean
        distance same as the of the farthest arriving station will be used.

        :return: pd.DataFrame of stations that satisfy range criteria
        """
        return pd.concat([self._add_primary_stations(max_station_dist),
                          self._add_temporary_stations()])

    def _swap_preferred_origin_with_iloc(self):
        self.event.preferred_origin = self.add_origin()

    @staticmethod
    def _delta(x, origin):
        return locations2degrees(x['latitude'], x['longitude'],
                                 origin.latitude, origin.longitude)

    @staticmethod
    def _match_sta(x, sta_phs_dict):
        return sta_phs_dict[x['station_code']] \
            if x['station_code'] in sta_phs_dict else None

    def _add_primary_stations(self, max_range):
        stations[DELTA] = stations.apply(self._delta, axis=1,
                                         origin=self.old_origin)
        max_dist, sta_phs_dict = self._farthest_station_dist()
        stations[PHASEHINT] = stations.apply(self._match_sta, axis=1,
                                             sta_phs_dict=sta_phs_dict)
        sel_stations = stations[stations[DELTA] < max_range / 100 * max_dist]
        return sel_stations

    def _farthest_station_dist(self):
        max_dist = -1.0
        sta_phs_dict = {}

        for arr in self.old_origin.arrivals:
            sta = stations_dict[
                arr.pick_id.get_referred_object().waveform_id.station_code
            ]
            dist = locations2degrees(self.old_origin.latitude,
                                     self.old_origin.longitude,
                                     sta.latitude, sta.longitude)
            if dist > max_dist:
                max_dist = dist

            if sta.station_code not in sta_phs_dict:
                sta_phs_dict[sta.station_code] = arr.phase
            else:
                sta_phs_dict[sta.station_code] = sta_phs_dict[
                    sta.station_code] + ' & ' + arr.phase

        return max_dist, sta_phs_dict

    def _add_temporary_stations(self):
        return pd.DataFrame()


class ILocCatalog(Catalog):
    """
    Class that supports event/catalog enhancement using iLoc.
    iLoc ref: http://www.seismology.hu/index.php/en/home/iloc
    """
    def __init__(self, event_xml, **kwargs):
        self.event_xml = event_xml
        self.cat = read_events(event_xml)
        self.orig_events = self.cat.events
        self.events = None

        new_comments = kwargs.get("comments", [])
        self.comments = new_comments + self.cat.comments
        self._set_resource_id(kwargs.get("resource_id", None))
        new_description = kwargs.get("description", "PST ILocCatalog Modified")
        self.description = (('orig_description: '
                             + self.cat.description + '; ')
                            if self.cat.description is not None else '') + \
                           ('description: ' + new_description)
        old_ci = self.cat.creation_info

        self.creation_info = CreationInfo(
            agency_id=old_ci.agency_id,
            agency_uri=old_ci.agency_uri,
            author=(('orig_author: ' + old_ci.author + '; ')
                    if old_ci.author is not None else '') + 'PST ILocCatalog',
            creation_info=UTCDateTime()
        )

        super(ILocCatalog, self).__init__(
            events=self.events,
            comments=self.comments,
            creation_info=self.creation_info,
            description=self.description,
            resource_id=self.resource_id
        )

    def update(self):
        for e in self.orig_events:
            iloc_ev = ILocEvent(e)()
            self.events.append(iloc_ev)


if __name__ == "__main__":
    cat = ILocCatalog(event_file)
    cat.update()
