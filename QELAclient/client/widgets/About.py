from appbase.mainWindowRessources.menuabout import MenuAbout

import client


class About(MenuAbout):
    '''
    Show the general information about QELA, license and terms of use
    '''
    FIRST_STEPS = '''\
This software corrects electroluminescence (EL) images of solar cells and modules.

<b>Supported cell types</b> <ul> \
    <li> mono and polycrystalline Si </li> \
    <li> currently NO HALF-CUT </li> \
</ul> \
\
<b>Supported module architectures</b> <ul> \
    <li> everything from 1x1 to 16x16 cells </li> \
</ul> \
\
<b>General Usage</b> <ol> \
    <li> Drag'n'drop all images and image-containing directories into 'Upload' tab. </li> \
    <li> Adjust options regarding camera calibration, image correction and post processing
       in 'Config' tab </li> \
    <li> Click on 'Upload' in 'Upload' Tab </li> \
    <li> All images will be uploaded into our server. You can see upload and processing 
       progress on the menu bar. Wait for the process to finish. There is an option within
       the 'Config' tab be receive a mail, once everything is done. </li> \
    <li> OPTIONAL: Validate camera- and perspective correction as well as the 
       module architecture.
       in the 'Check' Tab </li> \
    <li> Go to the 'Download' tab to download module reports, corrected EL images 
       and supplementary files. </li> \
</ol> \
<b>Tips for successful correction from camera-based distortion</b> \
<ul> \
    <li> For every new camera calibration or -parameter the first N images are taken \
        as calibration images. Before correcting images choose about 50 images of \
        (if possible different) PV cells or modules. Their position within the image\
        should vary and their brightness should be homogeneous. </li> \
    <li> You can check the calibration quality though clicking on 'View Report'\
    in the 'Configuration' Tab.</li> \
    <li> The calibration report also indicates whether the calibration is considered complete.\
        Once the calibration is complete, all images within the current project will be processed again. </li> \
    <li> In some cases this can dramatically improve the correction quality.</li> \
    <li> If a calibration does not generate desired results, remove (-) the current \
    and/or add (+) a new calibration file.</li> \
    <li> Every calibration is only valid for one camera-lens combination. Whenever you change\
        camera and/or lens you should change the camera calibration as well. </li> \
</ul>
\
<b>Tips for successful correction from perspective distortion</b> \
<ul> \
    <li> For every device the highest current image of the first (=oldest) measurement \
    will be taken as a reference for other measurements.</li> \
    <li> Ensure that this first image is of high quality. </li> \
    <li> Erroneously detected device posiiton can be manually corrected on the 'Check' Tab. </li> \
</ul>
'''

    def __init__(self, gui):
        super().__init__()
        self.setWindowIcon(gui.windowIcon())
        self.setLogo(client.ICON)
        addr = 'http://%s' % gui.server.address[0]
        self.setInfo(client.name,
                     client.__doc__, client.__author__, client.__email__,
                     client.__version__, client.__license__,
                     addr)
        self.setInstitutionLogo([(
            client.MEDIA_PATH.join('logo_seris.svg'),
            "http://www.seris.nus.edu.sg/")])

        self.addTab2('First steps', self.FIRST_STEPS)
        
        self.addTab2('Privacy Policy and Data Security', gui.server.page('privacy.htm'))
        
        self.addTab2('License', '''This program is free software: you can redistribute it and/or modify
it under the terms of the <b>GNU General Public License</b> as published by
the Free Software Foundation, either <b>version 3</b> of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses.</a>''')
        self.addTab('Terms of Use', gui.server.page('terms_of_use.htm'))
        
        self.addTab('Version info', '''\
This is an early test version. 
DONT USE IT IN PRODUCTION.
NO WARRANTY.

Known issues:
*
''')

    def addTab2(self, title, txt):
        self.addTab(title, txt.replace('\n', '<br>'))


if __name__ == '__main__':
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication([])

    w = About(None)

    w.show()
    app.exec_()
