from flask import Flask, render_template, request
from wtforms import Form, TextAreaField, validators
import os
import pickle
import numpy as np

app = Flask(__name__)

dir = os.path.dirname(__file__)
clf = pickle.load(open(os.path.join(dir, 'pkl_objects', 'clf.pkl'), 'rb'))

def classify(document):

    y = clf.predict([document])[0] + 1
    proba = np.max(clf.predict_proba([document]))

    return y, ("позитивный" if y >= 5 else "негативный"), proba

class ReviewForm(Form):
    moviereview = TextAreaField('',
                                [validators.DataRequired(),
                                validators.length(min=20)])
@app.route('/')

def index():
    form = ReviewForm(request.form)
    return render_template('reviewform.html', form=form)


@app.route('/results', methods=['POST'])
def results():
    form = ReviewForm(request.form)
    if request.method == 'POST' and form.validate():
        review = request.form['moviereview']
        y, label, proba = classify(review)
        return render_template('results.html',
                                content=review,
                                prediction=y,
                                assessment=label,
                                probability=round(proba*100, 2))
    return render_template('reviewform.html', form=form)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')