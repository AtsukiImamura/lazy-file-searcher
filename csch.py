import configparser
import os
import sys
import pathlib
import argparse
import re
import glob
import pickle
import codecs
from progressbar import ProgressBar
import time


# オプションファイルがないなら作成

saved_option_dir = os.path.normpath(
    "%s/data" % os.path.dirname(__file__))

if not os.path.exists(saved_option_dir):
    os.mkdir(saved_option_dir)

saved_option_path = os.path.normpath(
    "%s/options.pkl" % saved_option_dir)
if not os.path.exists(saved_option_path):
    with open(saved_option_path, "wb") as f_op:
        pickle.dump({}, f_op)

parser = argparse.ArgumentParser()

# == search options ==
parser.add_argument("-q", "--query",
                    help="""Lines in the file matched with given query is returned. 
                        The query can be simple string, also ban be regular expression.""")
parser.add_argument("-S",
                    help="""Use saved options identified with given key except for query.""")
parser.add_argument("-e", "--encoding", default=None,
                    help="[optional] All files are to be treated with given encoding.")
# parser.add_argument("-r", "--recursive", action="store_true",
#                     help="""[optional] Represents that it search files in given directories recursively.
#                         Note that this options is invalid when '-D' options is given.""")
# parser.add_argument("-E", action="store_true",
#                     help="""[optional] given query is treated as regular expression.""")
parser.add_argument("-t", "--target",  default="./*.*",
                    help="""[optional] Target directory subject to be searched. 
                        When directory is not given, all of the files in current directory will be searched. """)
parser.add_argument("-s", "--save",
                    help="""[optional] Save current options as given key.""")
# parser.add_argument("-wildcard_directory", "-D",
#                     help="""[optional] Target directory which includes wild card.
#                         All of directories matched with given expression are subject to be searched.
#                         Use of this option is more primary than '-d' option.
#                         """)
parser.add_argument("-i", "--ignore_linehead_to",  default=8, type=int,
                    help="""[optional] The character string of the specified length from the beginning of the line is ignored 
                        8 strings of head in every line is ignored by default.""")

# == output options ==
parser.add_argument("-g", "--show_only_filename", action="store_true",
                    help="""[optional] Result is shown as list of name of files which includes line(s) matched with given query.""")

parser.add_argument("--list", action="store_true",
                    help="""Show all saved options.""")

args = parser.parse_args()

if args.list:
    with open(saved_option_path, 'rb') as f_op:
        saved_options = pickle.load(f_op)
        print("-----------------------------------------")
        for key, options in saved_options.items():
            print("[ %s ]" % key)
            # for op_key, op in vars(options).items():
            options = vars(options)
            for op_key in ['query', 'encoding', 'target', 'ignore_linehead_to', 'show_only_filename']:
                print("    %20s: %s" % (op_key, options[op_key]))
        print("-----------------------------------------")
    sys.exit(0)

# 使用オプションの確定
options = {}
if args.S:  # 保存されたオプションを使う場合
    with open(saved_option_path, 'rb') as f_op:
        saved_options = pickle.load(f_op)
        if args.S not in saved_options:
            raise Exception("save key is not found in saved options.")
        options = saved_options[args.S]
        options.query = options.query if not args.query else args.query
else:  # 新たにオプションを指定する場合
    if not args.query:
        raise Exception(
            "query (with '-q') or option key (with '-S') is required.")
    options = args

print("---------------------------------------")
print("SEARCH OPTIONS:")
print("    query: %s" % options.query)
print("    encoding: %s" % options.encoding)
print("    target: %s" % options.target)
print("    ignore_linehead_to: %d" % options.ignore_linehead_to)

# 対象ファイルパス
target_file_paths = glob.glob(options.target,  recursive=True)

print("TARGET FILES:")
print("    amount: %d" % len(target_file_paths))
print("---------------------------------------")

progress_bar = ProgressBar(len(target_file_paths))
progress_bar.start()
# FOR DEBUG
# target_file_paths.append('./test/hoge.txt')

# 検索
results = []
pattern = None
try:
    pattern = re.compile(options.query)
except:
    print("ERROR!")
    print("    Something's gone wrong with given query. Check it out right now!")
    sys.exit(1)

if pattern is None:
    print("ERROR!")
    print("    Given query is shady...")
    sys.exit(1)

for f_idx, f_path in enumerate(target_file_paths):
    progress_bar.update(f_idx + 1)
    # ファイルの結果
    file_result = {
        'path': f_path,
        'matches': [],
        'errors': []
    }
    try:
        with open(f_path, 'r', encoding=options.encoding) as file:
            # 先頭指定文字数分カットした行
            lines = [l.rstrip('\n')[options.ignore_linehead_to:]
                     for l in file.readlines()]
            for line in lines:
                matchedList = pattern.findall(line)
                if not matchedList:
                    continue
                file_result['matches'].append(line)
    except PermissionError:
        file_result['errors'].append("PermissionError")
    except UnicodeDecodeError:
        file_result['errors'].append("UnicodeDecodeError")
    except ValueError:
        file_result['errors'].append("ValueError")
    except:
        file_result['errors'].append("FatalError")

    # FOR DEBUG
    # time.sleep(0.4)
    results.append(file_result)

progress_bar.finish()

# オプションの保存
if options.save:
    saved_options = None
    with open(saved_option_path, 'rb') as f_op:
        saved_options = pickle.load(f_op)
    with open(saved_option_path, "wb") as f_op:
        save_key = options.save
        options.save = None
        saved_options[save_key] = options
        pickle.dump(saved_options, f_op)

print("---------------------------------------")
print("MATCHES:")
for result in results:
    if len(result['matches']) == 0:
        continue
    sep = "" if options.show_only_filename else ":"
    print("    %s%s" % (result['path'], sep))
    if options.show_only_filename:
        continue
    for match in result['matches']:
        print("        %s" % match)

print("ERRORS:")
print("    amount: %d" %
      len(list(filter(lambda r: len(r['errors']) > 0, results))))

error_amount_per_type = {}
for result in results:
    for error in result['errors']:
        if error not in error_amount_per_type:
            error_amount_per_type[error] = 0
        error_amount_per_type[error] = error_amount_per_type[error] + 1
for type, amount in error_amount_per_type.items():
    print("        %s: %d" % (type, amount))

print("---------------------------------------")
