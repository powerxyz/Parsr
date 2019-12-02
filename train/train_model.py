import argparse
import os

import numpy as np
import pandas as pd
from sklearn import metrics
from sklearn.feature_selection import RFECV
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn_porter import Porter

from imblearn.over_sampling import SMOTE


parser = argparse.ArgumentParser(description='Train a decision tree to recognize headings.')
parser.add_argument('dataset_dir', help='folder containing the .csv files generated by build_dataset.py')
parser.add_argument('out_dir', help='folder in which to save the trained model')
args = parser.parse_args()

dataset_dir = args.dataset_dir
paths = os.listdir(dataset_dir)

x_train = []
y_train = []
for path in paths:
    df = pd.read_csv(os.path.join(dataset_dir, path), header=0)
    df['is_bold'] = df['is_bold'].apply(lambda x: 1 if x else 0)
    df['label'] = df['label'].apply(lambda x: 0 if x == 'paragraph' else 1)
    df['title_case'] = df['title_case'].apply(lambda x: 1 if x else 0)

    print(df.head())

    x_train.append([0,
                    df['font_size'][0] / df['font_size'][1],
                    df['is_bold'][0],
                    int(df['line'][0].isupper()),
                    0,
                    df['word_count'][0] / df['word_count'][1],
                    int(df['title_case'][0]),
                    0,
                    int(df['color'][1] == df['color'][0])])
    for i in range(len(df)):
        if i > 0 and i < len(df) - 1:
            prev_font_size = df['font_size'][i - 1]
            font_size = df['font_size'][i]
            next_font_size = df['font_size'][i + 1]

            x_train.append([font_size / prev_font_size,
                            font_size / next_font_size,
                            df['is_bold'][i],
                            int(df['line'][0].isupper()),
                            df['word_count'][i] / df['word_count'][i - 1],
                            df['word_count'][i] / df['word_count'][i + 1],
                            int(df['title_case'][i]),
                            int(df['color'][i] == df['color'][i - 1]),
                            int(df['color'][i] == df['color'][i + 1])])

    x_train.append([df['font_size'][len(df) - 1] / df['font_size'][len(df) - 2],
                    0,
                    df['is_bold'][len(df) - 1],
                    int(df['line'][0].isupper()),
                    df['word_count'][len(df) - 1] / df['word_count'][len(df) - 2],
                    0,
                    int(df['title_case'][len(df) - 1]),
                    int(df['color'][len(df) - 1] == df['color'][len(df) - 2]),
                    0])

    y_train = y_train + list(df['label'])

print(len(x_train))

smt = SMOTE()
x_train, y_train = smt.fit_sample(x_train, y_train)

print(len(x_train))

clf = DecisionTreeClassifier(min_samples_leaf=3, min_samples_split=2, criterion='entropy')
#clf = DecisionTreeClassifier(criterion='entropy')
clf = clf.fit(x_train, y_train)

selector = RFECV(clf, step=1, cv=5)
selector = selector.fit(x_train, y_train)
print(selector.support_)
print(selector.ranking_)

y_pred = clf.predict(x_train)
print('f1:', metrics.f1_score(y_pred, y_train))
print('IoU:', metrics.jaccard_score(y_pred, y_train))
print('AuC:', metrics.roc_auc_score(y_pred, y_train))

headings_x = []
headings_y = []
for x, y in zip(x_train, y_train):
    if y == 1:
        headings_y.append(1)
        headings_x.append(x)

y_pred = clf.predict(headings_x)

print('Accuracy:', metrics.accuracy_score(y_pred, headings_y))

porter = Porter(clf, language='js')
output = porter.export(embed_data=True)

headings_x_js = np.array(headings_x)
y_pred_js = porter.predict(headings_x_js)

print('Accuracy:', metrics.accuracy_score(y_pred_js, headings_y))

with open(os.path.join(args.out_dir, 'model.js'), mode='w+', encoding='utf8') as f:
    f.write('export ' + output)
