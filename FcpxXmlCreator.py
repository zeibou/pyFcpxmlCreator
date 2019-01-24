
import xml.etree.ElementTree as ET
import os
from pyHiLightExtractor import MultiFilesReader
from pyHiLightExtractor.MultiFilesReader import HiLightDescriptor
from pyHiLightExtractor.MultiFilesReader import VideoDescriptor
import datetime
from dataclasses import dataclass
from datetime import timedelta

fps = 60

@dataclass
class HilightMultiClick:
    hilight : HiLightDescriptor
    nb_clicks : int

@dataclass
class AssetDescriptor:
    id : str
    videoDesc : VideoDescriptor

@dataclass
class ClipDescriptor:
    name : str
    ref : str
    start : float
    duration : float

def add_mpeg_asset(root, video_desc):
    res = root.find("resources")
    nb_res = len(res)
    #for e in res:
    #    print(e, nb_res)
    new_asset = ET.Element("asset")
    asset_id = "r"+str(nb_res + 1)
    new_asset.set("id", asset_id)
    new_asset.set("name", get_asset_name(video_desc.name))
    new_asset.set("src", "file://" + video_desc.path)
    res.append(new_asset)
    return AssetDescriptor(asset_id, video_desc)


def build_title_element(title_asset_id, text, offset):
    title_elt = ET.Element("title")
    title_elt.set("duration", "5s")
    title_elt.set("offset", offset)
    title_elt.set("start", "21605200/6000s")
    #offset="21597900/6000s" ref="r2" duration="59900/6000s" start="21605200/6000s"
    title_elt.set("lane", "1")
    title_elt.set("name", "title")
    title_elt.set("ref", title_asset_id)
    param_pos_elt = ET.Element("param")
    param_pos_elt.set("key", "9999/10902/10736/1/100/101")
    param_pos_elt.set("name", "Position")
    param_pos_elt.set("value", "245.11 -487.675")
    param_ali_elt = ET.Element("param")
    param_ali_elt.set("key", "9999/10902/10736/2/354/1156453060/401")
    param_ali_elt.set("name", "Alignment")
    param_ali_elt.set("value", "1 (Center)")
    text_elt = ET.Element("text")
    text_style_elt = ET.Element("text-style")
    text_style_elt.set("ref", "ts1")
    text_style_elt.text = text
    text_style_def_elt = ET.Element("text-style-def")
    text_style_def_elt.set("id", "ts1")
    text_style2_elt = ET.Element("text-style")
    text_style2_elt.set("alignment", "center")
    text_style2_elt.set("font", "Chalkduster")
    text_style2_elt.set("fontColor", "0.933208 1 0.925737 1")
    text_style2_elt.set("fontFace", "Regular")
    text_style2_elt.set("fontSize", "119")
    text_style2_elt.set("strokeColor", "0.000231543 0.00478462 0.0900643 1")
    text_style2_elt.set("strokeWidth", "4")

    title_elt.append(param_pos_elt)
    title_elt.append(param_ali_elt)
    text_elt.append(text_style_elt)
    title_elt.append(text_elt)
    text_style_def_elt.append(text_style2_elt)
    title_elt.append(text_style_def_elt)

    return title_elt

def get_asset_name(filepath):
    filename = os.path.basename(filepath)
    return os.path.splitext(filename)[0]

def open_template(template_xml_file):
    if not os.path.exists(template_xml_file):
        raise ValueError("template file not found")
    return ET.parse(template_xml_file)

def add_all_mpeg_assets(root, folder, assets):
    print("Loading videos...")
    for h in MultiFilesReader.get_all_videos(folder, endswith=".mp4"):
        if not h.name in assets:
            assets[h.name] = add_mpeg_asset(root, h)
    for a in assets: print(a, assets[a])
    return assets

def add_all_clips(spine, folder, assets, title_text):
    clip_descriptions = []
    for h in detect_multi_clicks(MultiFilesReader.get_all_hilights(folder, endswith=".mp4"), nb_seconds_interval = 2):
        hilight, duration, end_offset = h.hilight, *get_offset_bounds(h.nb_clicks)
        for clip in compute_clips(assets, hilight, duration, end_offset):
            clip_descriptions.append(clip)

    for i, clip_desc in enumerate(merge_clips(clip_descriptions)):
        clip = create_clip(clip_desc)
        spine.append(clip)

        # add title
        if i == 0:
            start = f"{int(clip_desc.start) + 3}s"
            clip.append(build_title_element("r2", title_text, start))

def get_offset_bounds(hilight_click_number):
    return (10 * hilight_click_number, 1)


def merge_clips(clips): # list of ClipDescriptor
    # todo
    return clips

def compute_clips(assets, hilight, duration_seconds, end_offset_seconds):
    start_seconds = hilight.local_time.total_seconds() - duration_seconds - end_offset_seconds
    if start_seconds >= 0:
        yield ClipDescriptor(hilight.name, assets[hilight.name].id, start_seconds, duration_seconds)
    else:
        # if hilight is early on a video, we need to insert the end of the previous video
        # adding end of the first clip
        previous = assets[hilight.name].videoDesc.previous_name
        if previous:
            previous_video_duration = assets[previous].videoDesc.total_time
            yield ClipDescriptor(previous, assets[previous].id, previous_video_duration + start_seconds, -start_seconds)

        # adding beginning of the second clip
        yield ClipDescriptor(hilight.name, assets[hilight.name].id, 0, duration_seconds + start_seconds)

def create_clip(clip_desc):
    print(clip_desc)
    clip = ET.Element("asset-clip")
    clip.set("name", get_asset_name(clip_desc.name))
    clip.set("ref", clip_desc.ref)
    clip.set("start", f"{int(clip_desc.start * fps)*100}/{fps}00s")
    clip.set("duration", f"{int(clip_desc.duration * fps)*100}/{fps}00s")
    return clip


def detect_multi_clicks(hilights, nb_seconds_interval=2):
    # todo loop reverse to keep first click of multi clicks
    # output detected multi clicks + discarded extra clicks
    # return filtered hilights with number of clicks associated (HilightMultiClick)
    for h in hilights:
        yield HilightMultiClick(h, 1)



if __name__ == '__main__':
    date = "2019-01-14"
    d = datetime.datetime.strptime(date, "%Y-%m-%d")
    title_text = d.strftime("%B %d, %Y")

    template_path = "/Users/nicolas.seibert/Documents/Projects/pyFcpxmlCreator/template.fcpxml"
    tree = open_template(template_path)
    assets = dict()
    folder = f"/Users/nicolas.seibert/Documents/foot/{date}/"
    add_all_mpeg_assets(tree.getroot(), folder, assets)

    spine = tree.getroot().find("library").find("event").find("project").find("sequence").find("spine")
    add_all_clips(spine, folder, assets, title_text)
    #<asset-clip name="GH030065" ref="r5" duration="20s" start="10s" format="r3">

    tree.write(f"/Users/nicolas.seibert/Documents/foot/{date}/autogen.fcpxml")