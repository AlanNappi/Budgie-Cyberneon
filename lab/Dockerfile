# CyberNeon test lab: the real Budgie 10.9 of Ubuntu 24.04 on a virtual X screen. Nothing touches the host desktop.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    budgie-core budgie-desktop budgie-showtime-applet ubuntu-budgie-themes \
    xvfb xauth x11-utils x11-xserver-utils x11-apps xdotool wmctrl libgl1-mesa-dri libglx-mesa0 \
    dbus dbus-x11 dconf-cli dconf-gsettings-backend libglib2.0-bin gsettings-desktop-schemas \
    python3 python3-gi python3-gi-cairo python3-cairo python3-pil python3-dbus python3-dbusmock \
    gir1.2-gtk-3.0 gir1.2-wnck-3.0 gir1.2-pango-1.0 gir1.2-notify-0.7 libnotify-bin \
    conky-all nemo tilix adwaita-icon-theme hicolor-icon-theme fontconfig curl grub-common \
    iproute2 procps systemd imagemagick gcc libc6-dev libcanberra0 libcanberra-gtk3-0 \
    plymouth plymouth-themes
RUN useradd -m -s /bin/bash netrunner && mkdir -p /out
RUN apt-get install -y --no-install-recommends librsvg2-common
# the second app menu (Slingshot, applet name AppMenu) many Ubuntu Budgie top bars have: the pods take it out
RUN apt-get install -y --no-install-recommends budgie-applications-menu-applet
