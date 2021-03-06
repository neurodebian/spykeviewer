from spykeviewer.plugin_framework.analysis_plugin import AnalysisPlugin

from PyQt4.QtGui import QMessageBox
import guidata.dataset.dataitems as di

import spykeutils.plot as plot
from spykeutils.spyke_exception import SpykeException
import spykeutils.plot.helper as helper

class SignalPlotPlugin(AnalysisPlugin):
    """ Signal Plot
    """
    domain = di.ChoiceItem('Domain', ('Recording Channel Group',
                                           'Recording Channel'))
    show_events = di.BoolItem('Show events', default=True)
    show_epochs = di.BoolItem('Show epochs', default=True)
    show_spikes = di.BoolItem('Show spike events', default=False)
    show_waveforms = di.BoolItem('Show spike waveforms', default=True)

    def get_name(self):
        return 'Signal Plot'

    @helper.needs_qt
    def start(self, current, selections):
        if self.domain == 0: # Channel groups
            num = current.num_analog_signal_arrays()
        else: # Single channels
            num = current.num_analog_signals()

        # Handle too little and too much data
        if num < 1:
            raise SpykeException('No signals selected!')
        if num > 1:
            ans = QMessageBox.question(None, 'Caution!',
                ('Do you really want to create %d plots ' % num) +
                '(one for each signal)?', QMessageBox.Yes, QMessageBox.No)
            if ans == QMessageBox.No:
                return

        current.progress.begin('Loading signals...')
        if self.domain == 0: # Channel groups
            signals = current.analog_signal_arrays_by_channelgroup_and_segment()
        else: # Single channels
            signals = current.analog_signals_by_channel_and_segment()

        # Load supplemental data
        events = None
        if self.show_events:
            current.progress.set_status('Loading events')
            events = current.events()

        epochs = None
        if self.show_epochs:
            current.progress.set_status('Loading epochs')
            epochs = current.epochs()

        spike_trains = None
        if self.show_spikes:
            current.progress.set_status('Loading spike trains')
            spike_trains = current.spike_trains_by_segment()

        spikes = None
        if self.show_waveforms:
            current.progress.set_status('Loading spikes')
            spikes = current.spikes_by_segment()

        current.progress.done()

        # Create a plot for each segment
        for chandict in signals.itervalues():
            for seg, sig in chandict.iteritems():
                seg_events = None
                if events and events.has_key(seg):
                    seg_events = events[seg]

                seg_epochs = None
                if epochs and epochs.has_key(seg):
                    seg_epochs = epochs[seg]

                seg_trains = None
                if spike_trains and spike_trains.has_key(seg):
                    seg_trains = spike_trains[seg]

                seg_spikes = None
                if spikes and spikes.has_key(seg):
                    seg_spikes = spikes[seg]

                if self.domain == 0: # Channel groups
                    plot.signal_array(sig, events=seg_events,
                        epochs=seg_epochs, spike_trains=seg_trains,
                        spike_waveforms=seg_spikes)
                else: # Single channels
                    for s in sig:
                        plot.signal(s, events=seg_events,
                            epochs=seg_epochs, spike_trains=seg_trains,
                            spike_waveforms=seg_spikes)