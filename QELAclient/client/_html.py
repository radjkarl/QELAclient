
def imageToHTML(path,  width=None, height=None):
    imsize = ''
    if width is not None:
        imsize += 'width="%s"' % width
    if height is not None:
        imsize += 'height="%s"' % height
    return "<img src='%s' %s>" % (path, imsize)


def toHtml(txt):
    return '<html>' + txt.replace('\n', '<br>') + '</html>'

# following works, but is slower and actually only needed, if image in in
# buffer

# def imageToolTip(path, width, height):
#     buffer = QtCore.QBuffer()
#     buffer.open(QtCore.QIODevice.WriteOnly)
#
#     pixmap = QtGui.QIcon(path).pixmap(QtCore.QSize(width, height))
#
#     pixmap.save(buffer, "PNG", quality=100)
#     image = bytes(buffer.data().toBase64()).decode()
# #     html = '<img src="data:image/png;base64,{}">'.format(image)
#     return  "<img src='%s'>" % path
#
