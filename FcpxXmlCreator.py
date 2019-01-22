
import xml.etree.ElementTree as ET
import os
from pyHiLightExtractor import MultiFilesReader
from pyHiLightExtractor.MultiFilesReader import HiLightDescriptor
from pyHiLightExtractor.MultiFilesReader import VideoDescriptor
import datetime
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class HilightMultiClick:
    hilight : HiLightDescriptor
    nb_clicks : int

@dataclass
class AssetDescriptor:
    id : str
    videoDesc : VideoDescriptor

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
    for h in MultiFilesReader.get_all_videos(folder, endswith=".mp4"):
        if not h.name in assets:
            assets[h.name] = add_mpeg_asset(root, h)
    return assets

def add_all_clips(spine, folder, assets, title_text, timeSeconds):
    for i, h in enumerate(detect_multi_clicks(MultiFilesReader.get_all_hilights(folder, endswith=".mp4"), nb_seconds_interval = 2)):
        clip = add_clip(spine, assets, h, 10, 0)

        # add title
        if i == 0:
            start = f"{h.local_time.seconds - timeSeconds + 3}s"
            clip.append(build_title_element("r2", title_text, start))


def add_clip(spine, assets, hilight, duration_seconds, end_offset_seconds):
    clip = ET.Element("asset-clip")
    clip.set("name", get_asset_name(hilight.name))
    clip.set("ref", assets[hilight.name].id)
    start_seconds = hilight.local_time.seconds - duration_seconds - end_offset_seconds
    if start_seconds >= 0:
        clip.set("start", f"{start_seconds}s")
        clip.set("duration", f"{duration_seconds}s")
        spine.append(clip)
    else:
        # adding end of the first clip
        # todo if hilight is early on a video, we need to insert the end of the previous video

        # adding beginning of the second clip
        clip.set("start", "0s")
        clip.set("duration", f"{duration_seconds + start_seconds}s")
        spine.append(clip)
    return clip


def detect_multi_clicks(hilights, nb_seconds_interval=2):
    # todo loop reverse to keep first click of multi clicks
    # output detected multi clicks + discarded extra clicks
    # return filtered hilights with number of clicks associated (HilightMultiClick)
    for h in hilights:
        yield h



if __name__ == '__main__':
    date = "2019-01-14"
    d = datetime.datetime.strptime(date, "%Y-%m-%d")
    title_text = d.strftime("%B %d, %Y")

    template_path = "/Users/nicolas.seibert/Documents/foot/2019-01-14/template.fcpxml"
    tree = open_template(template_path)
    assets = dict()
    folder = f"/Users/nicolas.seibert/Documents/foot/{date}/"
    add_all_mpeg_assets(tree.getroot(), folder, assets)

    spine = tree.getroot().find("library").find("event").find("project").find("sequence").find("spine")
    add_all_clips(spine, folder, assets, title_text, 10)
    #<asset-clip name="GH030065" ref="r5" duration="20s" start="10s" format="r3">

    for a in assets: print(a, assets[a])
    tree.write("/Users/nicolas.seibert/Documents/foot/2019-01-14/2019-01-14-autogen.fcpxml")