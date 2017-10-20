"""
GF Variable beta variable fonts:

Generate variable fonts with fontmake from .glyphs sources.

Script traverses a directory tree and will generate var fonts if it
encounters a .glyphs file with at least 2 masters and more than 3
instances.

"""

import glyphsLib
import os
import subprocess
from os.path import basename
import sys
import shutil
import re
import fonts_public_pb2 as fonts_pb2
from google.protobuf import text_format


SOURCE_FOLDERS = [
    'source',
    'sources',
]

METADATA_CATEGORIES = {
    'SERIF': 'Serif',
    'SANS_SERIF': 'Sans Serif',
    'DISPLAY': 'Display',
    'HANDWRITING': 'Handwriting',
    'MONOSPACE': 'Monospace',
}


def git_url(copyright):
    '''Return the url from a string
    
    e.g:
    Copyright the ABC Project Authors (https://www.github.com/mrc/sans) ->
    https://www.github.com/mrc/sans
    '''
    try:
        return re.search(r'http[a-zA-Z0-9\:\.\/]{1,256}', copyright).group(0)
    except:
        all
        return 'None'


def find_mm_compatible_glyphs_files(path):
    """Find .glyphs file which can be generated into variable fonts.

    The criterea is a file which contains 2 masters with more than 3
    instances"""
    families = []
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            if '.glyphs' in f and basename(root) in SOURCE_FOLDERS:
                glyphs_path = os.path.join(root,f)
                try:
                    with open(glyphs_path, 'rb') as glyphs_file:
                        glyphs_source = glyphsLib.load(glyphs_file)

                        master_count = len(glyphs_source['fontMaster'])
                        instance_count = len(glyphs_source['instances'])
                        # Get fonts which successfully use MM
                        if master_count >= 2 and instance_count >= 3 and \
                            master_count != instance_count:
                                print 'Adding: %s' % root
                                families.append(glyphs_path)
                except: # TODO error log and catch these exceptions betters
                    print 'Cannot add %s' % f
                    all
    return families


def rename_fonts(path):
    for f in os.listdir(path):
        if f.endswith('.ttf'):
            new_f = f.replace('VTBeta', 'VFBeta')
            new_f = new_f.replace('-VF.ttf', '.ttf')
            old_name = os.path.join(path, f)
            new_name = os.path.join(path, new_f)
            os.rename(old_name, new_name)


def cleanup_folders(vf_family_dir_name):
    """Remove fontmake gen folders and rename variable_ttf folder
    to familyname"""
    if not os.path.isdir(vf_family_dir_name):
        os.rename('variable_ttf', vf_family_dir_name)
    else:
        new_files = os.listdir('variable_ttf')
        for f in new_files:
            os.rename(
                os.path.join('variable_ttf', f),
                os.path.join(vf_family_dir_name, f),
                )
        shutil.rmtree('variable_ttf')

    # Remove temp folders needed to generate variable fonts
    shutil.rmtree('master_ufo')
    shutil.rmtree('master_ttf_interpolatable')


def create_early_access_file(path, category):
    """Early Access files are used in https://fonts.google.com/earlyaccess
    to determine family catagory"""
    early_acc_filename = 'EARLY_ACCESS.category'
    early_acc_path = os.path.join(path, early_acc_filename)
    if not early_acc_filename in os.listdir(path):
        print 'Writing EARLY_ACCESS.category %s' % early_acc_path
        with open(early_acc_path, 'w') as acc:
            acc.write(category)


def _get_metadata_category(meta_file):
    category = None
    metadata = fonts_pb2.FamilyProto()
    with open(meta_file, "rb") as meta:
          text_format.Parse(meta.read(), metadata)
          category = metadata.category
    return METADATA_CATEGORIES[category]


def cp_file(src, dest):
    """If a file does not exist, copy it"""
    if not os.path.exists(dest):
        shutil.copyfile(src, dest)


def create_description_file(path, category, designer, copyright):
    """Create basic html doc from glyphs source. 
    May need hand editing if the copyright does not contain a url"""
    with open('DESCRIPTION.en_us_temp.html', 'r') as tmp_doc:
        desc_txt = tmp_doc.read()
        desc_txt = desc_txt.replace(
            '{{ designer }}', designer
        )
        desc_txt = desc_txt.replace(
            '{{ category }}', category
        )
        
        proj_url = git_url(copyright)
        desc_txt = desc_txt.replace('{{ git_url }}', proj_url)

        desc_file = os.path.join(path, 'DESCRIPTION.en_us.html')
        with open(desc_file, 'w') as desc_doc:
            desc_doc.write(desc_txt)


def get_glyphs_key(glyphs_path, key):
    with open(glyphs_path, 'rb') as glyphs_data:
        glyphs_source = glyphsLib.load(glyphs_data)
        return glyphs_source[key]


def set_family_name(glyphs_path, old_name, new_name):
    """Change the name of a family in a .glyphs file"""
    # TODO (Marc Foley): This is hacky, update when
    # https://github.com/googlei18n/glyphsLib/issues/246 is fixed
    old_data, new_data = '', ''
    with open(glyphs_path) as glyphs_file:
        data = glyphs_file.read()
        new_data = re.sub(r'familyName = .*;',
                           'familyName = "%s";' % new_name, data)
        # renamed_data = renamed_data.replace(curr_name, new_name)
    os.remove(glyphs_path)
    with open(glyphs_path, 'w') as glyphs_file:
        glyphs_file.write(new_data)


def copy_files_to_folder(src_paths, dst):
    if not os.path.isdir(dst):
        os.mkdir(dst)
    [shutil.copy(f, dst) for f in src_paths]



def gen_beta_vf_project(glyphs_path, ofl_path):
    """Generate .glyph file into VF font project, based on
    https://github.com/google/fonts/pull/724"""
    glyphs_source = glyphsLib.load(open(glyphs_path, 'rb'))
    family_name = glyphs_source['familyName']
    designer = glyphs_source['designer']
    copyright = glyphs_source['copyright']

    # Generate variable font with 'VF Beta appended to font name'
    beta_family_name = family_name + ' VF Beta'
    set_family_name(glyphs_path, family_name, beta_family_name)
    # Generate variable font via cmdline fontmake
    # TODO (Marc Foley) just use fontmake properly
    subprocess.call(['fontmake', '-g', glyphs_path, '-o', 'variable'])

    # Folder cleanup
    ofl_family_dir = family_name.lower().replace(' ', '')
    vf_family_dir = ofl_family_dir + 'vfbeta' 
    rename_fonts('variable_ttf')
    cleanup_folders(vf_family_dir)

    # Copy over OFL.txt license files
    ofl_txt = os.path.join(ofl_path, ofl_family_dir, 'OFL.txt')
    vf_ofl_txt = os.path.join(vf_family_dir, 'OFL.txt')
    cp_file(ofl_txt, vf_ofl_txt)

    # Create early access file and description
    meta_path = os.path.join(ofl_path, ofl_family_dir, 'METADATA.pb')
    category = _get_metadata_category(meta_path)
    create_early_access_file(vf_family_dir, category)
    create_description_file(vf_family_dir, category, designer, copyright)


def main(path, ofl_path):
    failed_families = []
    mm_families_paths = find_mm_compatible_glyphs_files(path)
    if not os.path.isdir('mm_src'):
        os.mkdir('mm_src')
    else:
        shutil.rmtree('mm_src')
    copy_files_to_folder(mm_families_paths, 'mm_src')

    for f in os.listdir('mm_src'):
        if f.endswith('.glyphs'):
                src_path = os.path.join('mm_src', f)
                try:
                    gen_beta_vf_project(src_path, ofl_path)
                except:
                    all # TODO (Marc Foley): proper error handling
                    failed_families.append(f)
    print 'failed on [%s]' % ', '.join(failed_families)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'ERROR: include tree path to .glyphs sources and ofl dir'
    else:
        main(sys.argv[1], sys.argv[2])
