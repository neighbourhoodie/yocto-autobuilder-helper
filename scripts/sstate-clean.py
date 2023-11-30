import os
f = open('/mnt/tank/yocto/sstate-matime.log', 'r')
for line in f.readlines():
  ssdir, ssfile = os.path.split(line[61:-1])
  if os.path.isfile(os.path.join('/mnt/tank/yocto/autobuilder/autobuilder.yoctoproject.org/pub', ssdir, ssfile)):
    if not os.path.isdir(os.path.join('/mnt/tank/yocto/sstate-to-remove-30', ssdir)):
      #print("Creating ", os.path.join('/mnt/tank/yocto/sstate-to-remove-30', ssdir))
      os.makedirs(os.path.join('/mnt/tank/yocto/sstate-to-remove-30', ssdir))
    os.rename(
       os.path.join('/mnt/tank/yocto/autobuilder/autobuilder.yoctoproject.org/pub', ssdir, ssfile),
       os.path.join('/mnt/tank/yocto/sstate-to-remove-30', ssdir, ssfile)
    )

