# These do not actually need to be imported at this time
# This is just a convenient way to make pyinstaller find them
if False:
    import spykeviewer
    import spykeutils
    import spykeutils.plot

# Use new style API
import sip
sip.setapi('QString', 2)
sip.setapi('QDate', 2)
sip.setapi('QDateTime', 2)
sip.setapi('QTextStream', 2)
sip.setapi('QTime', 2)
sip.setapi('QVariant', 2)
sip.setapi('QUrl', 2)
sip.setapi('QVariant', 2)