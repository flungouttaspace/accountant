from decimal import InvalidOperation, localcontext
from pathlib import Path
from flask import Flask, redirect, render_template, request, url_for
from firma import Manager


def utworz_aplikacje(plik_danych=None):
    app = Flask(__name__)
    app.config['PLIK_DANYCH'] = Path(plik_danych) if plik_danych else Path(__file__).with_name('dane.txt')

    def wczytaj_managera():
        manager = Manager(app.config['PLIK_DANYCH'])
        manager.execute('wczytaj')
        return manager

    @app.route('/', methods=['GET', 'POST'])
    def glowna():
        blad = ''
        status = 200
        with localcontext() as kontekst:
            kontekst.prec = 60
            try:
                manager = wczytaj_managera()
            except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
                return render_template('blad.html', blad='Nie można odczytać pliku danych. Sprawdź dane.txt.'), 500
            if request.method == 'POST':
                try:
                    komenda = request.form.get('komenda', '')
                    if komenda not in ('saldo', 'zakup', 'sprzedaż'):
                        raise ValueError('Nieprawidłowa operacja.')
                    if komenda == 'saldo' and not request.form.get('komentarz', '').strip():
                        raise ValueError('Wpisz komentarz do zmiany salda.')
                    manager.formularz = request.form
                    manager.execute(komenda)
                    return redirect(url_for('glowna', zapisano=1))
                except (ValueError, InvalidOperation) as error:
                    blad = str(error)
                    status = 400
                except OSError:
                    blad = 'Nie udało się zapisać operacji. Sprawdź dostęp do pliku danych.'
                    status = 500
                # Po błędzie pokazujemy dane zapisane w pliku.
                manager = wczytaj_managera()
            return render_template('index.html', manager=manager, blad=blad,
                                   zapisano=request.args.get('zapisano') == '1',
                                   pola=request.form), status

    @app.route('/historia/')
    @app.route('/historia/<int(signed=True):line_from>/<int(signed=True):line_to>/')
    def historia(line_from=None, line_to=None):
        try:
            manager = wczytaj_managera()
        except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
            return render_template('blad.html', blad='Nie można odczytać pliku danych.'), 500
        blad = ''
        status = 200
        wpisy = list(enumerate(manager.historia))
        if line_from is not None:
            if not 0 <= line_from <= line_to < len(wpisy):
                blad = 'Nieprawidłowy zakres. Indeksy zaczynają się od 0. Liczba operacji: ' + str(len(wpisy))
                wpisy = []
                status = 400
            else:
                wpisy = wpisy[line_from:line_to + 1]
        return render_template('historia.html', wpisy=wpisy, blad=blad,
                               liczba=len(manager.historia), od=line_from, do=line_to), status

    @app.get('/historia/zakres/')
    def zakres():
        od = request.args.get('od', '')
        do = request.args.get('do', '')
        if not od and not do:
            return redirect(url_for('historia'))
        try:
            return redirect(url_for('historia', line_from=int(od), line_to=int(do)))
        except ValueError:
            return render_template('blad.html', blad='Podaj obie granice zakresu jako liczby całkowite.'), 400

    return app


if __name__ == '__main__':
    utworz_aplikacje().run(host='127.0.0.1', port=5000, threaded=False)
