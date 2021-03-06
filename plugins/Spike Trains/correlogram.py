from spykeviewer.plugin_framework.analysis_plugin import AnalysisPlugin
import spykeutils.plot
import guidata.dataset.dataitems as di
import quantities as pq

class CorrelogramPlugin(AnalysisPlugin):
    bin_size = di.FloatItem('Bin size', 1.0, 0.1, 10000.0, unit='ms')
    cut_off = di.FloatItem('Cut off', 50.0, 2.0, 10000.0, unit='ms')
    data_source = di.ChoiceItem('Data source', ('Units', 'Selections'))
    border_correction = di.BoolItem('Border correction', default=True)

    def get_name(self):
        return 'Correlogram'

    def start(self, current, selections):
        if self.data_source == 0:
            d = current.spike_trains_by_unit()
        else:
            # Prepare dictionary for correlogram():
            # One entry of spike trains for each selection
            d = {}
            for i,s in enumerate(selections):
                d[plot.create_unit(s.name, i)] = s.spike_trains()

        spykeutils.plot.cross_correlogram(d, self.bin_size*pq.ms,
            self.cut_off*pq.ms, self.border_correction,
            progress=current.progress)

