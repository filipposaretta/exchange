import random
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages, auth
from django.contrib.auth.models import User
from .models import Wallet, Trans
from .forms import Buy, Sell
from django.utils import timezone
from django.db.models import Q


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            # correct username and password login the user
            auth.login(request, user)
            return redirect('user_details')
        else:
            messages.error(request, 'Errore: username/password errati')

    return render(request, 'app/login.html')


@login_required
def logout(request):
    auth.logout(request)
    return render(request, 'app/logout.html')


@login_required
def user_details(request):
    user = get_object_or_404(User, id=request.user.id)
    try:
        user.bit_user = Wallet.objects.get(username=request.user.username).bitcoin
        user.dol_user = Wallet.objects.get(username=request.user.username).dollars
        user.wallet = True
        return render(request, 'app/user_details.html', {'user': user})
    except Wallet.DoesNotExist:
        user.wallet = False
        return render(request, 'app/user_details.html', {'user': user})


def welcome(request):
    return render(request, 'app/welcome.html')

def signup(request):
    if request.method == 'POST':
        f = UserCreationForm(request.POST)
        if f.is_valid():
            f.save()
            messages.success(request, 'Account creato correttamente')
            return render(request, 'app/welcome.html')
        else:
            messages.add_message(request, messages.INFO,
                                 'Ops, o l\' account esiste già o hai sbagliato a copiare la password')
            return render(request, 'app/signup.html', {'form': f})
    else:
        f = UserCreationForm()
        return render(request, 'app/signup.html', {'form': f})


@login_required
def wallet(request):
    user = get_object_or_404(User, id=request.user.id)

    # arrotonda sempre di 2 cifre decimali
    try:
        user.bitcoin = round(Wallet.objects.get(username=request.user.username).bitcoin, 2)
        user.dollars = round(Wallet.objects.get(username=request.user.username).dollars, 2)
        return render(request, 'app/wallet.html', {'user': user})

    #se non esiste crealo tu
    except Wallet.DoesNotExist:  # new user
        user.bitcoin = round(random.random() * 10, 2)
        while user.bitcoin < 1:
            user.bitcoin = round(random.random() * 10, 2)
        user.dollars = round(random.random() * 150000, 2)
        user.save()
        Wallet.objects.create(username=user.username, bitcoin=user.bitcoin, dollars=user.dollars,
                              dollars_init=user.dollars, bitcoin_init=user.bitcoin)
        return render(request, 'app/wallet.html', {'user': user})


@login_required
def buy_new(request):   # nuovo acquisto
    if request.method == "POST":
        form = Buy(request.POST)
        if form.is_valid():
            trans_buyer = form.save(commit=False)
            trans_buyer.creator = request.user.username  # user
            trans_buyer.buy_in = trans_buyer.buy
            trans_buyer.sell_in = trans_buyer.sell
            trans_seller = ""
            try:
                dollars_buyer = Wallet.objects.get(username=trans_buyer.creator).dollars  # $ del buyer
                trans_buyer.dollars_trans = trans_buyer.price_1B_in * trans_buyer.buy  # voglio solo valori positivi

                # cerco se il BUYER ha disponibilità economica
                total_trans_buy = Trans.objects.all().filter(ended=False, good=True, sell=0, creator=trans_buyer.creator)

                dollari_totali_in_acquisto = trans_buyer.dollars_trans
                for i in total_trans_buy:
                    dollari_totali_in_acquisto += Trans.objects.get(_id=i._id).buy

                if dollari_totali_in_acquisto <= dollars_buyer:
                    if 0 < trans_buyer.dollars_trans < dollars_buyer:  # se è buona
                        Trans.objects.create(creator=trans_buyer.creator, published_date=timezone.now(), good=True,
                                             buy=round(trans_buyer.buy, 2), sell=0.0, buy_in=round(trans_buyer.buy_in, 2), sell_in=0.0,
                                             price_1B_in=round(trans_buyer.price_1B_in, 2))

                        trans_buyer.id_buyer = Trans.objects.latest('published_date')._id

                        #   inizializzo le variabili
                        tmp_price_1b = trans_buyer.price_1B_in  # valore di 1B BUYER
                        tmp_price_1b_seller = 0
                        quantity = 0
                        seller = ""  # tmp winner SELLER
                        id_seller = 0

                        #   cerco le non self transactions
                        total_trans = Trans.objects.all().filter(ended=False, good=True, buy=0).exclude(
                            creator=trans_buyer.creator)

                        for k in total_trans:  # cerco il SELLER
                            trans_seller_tmp = Trans.objects.get(_id=k._id)

                            if tmp_price_1b > trans_seller_tmp.price_1B_in > tmp_price_1b_seller:  # buono
                                trans_seller = trans_seller_tmp
                                tmp_price_1b_seller = trans_seller.price_1B_in
                                seller = trans_seller.creator
                                id_seller = trans_seller._id

                                if trans_seller.sell >= trans_buyer.buy:  # match completo
                                    quantity = trans_buyer.buy
                                else:  # match parziale
                                    quantity = trans_seller.sell

                        if seller != "":  # cerco se ho trovato il SELLER
                            trans_buyer.winner = seller
                            trans_buyer.price_1B_end = tmp_price_1b
                            trans_buyer.total_B_exchanged = quantity
                            bitcoin_rimasti_seller = trans_seller.sell - quantity
                            bitcoin_rimasti_buyer = trans_buyer.buy - quantity

                            # SELLER
                            if bitcoin_rimasti_seller == 0:  # complete seller
                                Trans.objects.filter(_id=id_seller).update(
                                    ended=True,
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    winner=trans_buyer.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    sell=0.0)

                            elif bitcoin_rimasti_seller > 0:  # partial
                                Trans.objects.filter(_id=id_seller).update(sell=bitcoin_rimasti_seller)
                                Trans.objects.create(
                                    creator=trans_seller.creator,
                                    ended=True,
                                    good=True,
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    winner=trans_buyer.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    sell=0.0, sell_in=round(quantity, 2))

                            # BUYER
                            if bitcoin_rimasti_buyer == 0:
                                Trans.objects.filter(_id=trans_buyer.id_buyer).update(
                                    ended=True,
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    winner=trans_seller.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    buy=0.0)

                            elif bitcoin_rimasti_buyer > 0:  # partial
                                Trans.objects.filter(_id=trans_buyer.id_buyer).update(buy=bitcoin_rimasti_buyer)
                                Trans.objects.create(
                                    creator=trans_buyer.creator,
                                    good=True,
                                    ended=True,
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    winner=trans_seller.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    buy=0, buy_in=round(quantity, 2))

                            #aggiorno i Wallet
                            Wallet.objects.filter(username=trans_buyer.creator).update(
                                dollars=round(Wallet.objects.get(
                                    username=trans_buyer.creator).dollars - tmp_price_1b * quantity, 2),
                                bitcoin=round(Wallet.objects.get(username=trans_buyer.creator).bitcoin + quantity, 2))

                            Wallet.objects.filter(username=trans_seller.creator).update(
                                dollars=round(Wallet.objects.get(
                                    username=trans_seller.creator).dollars + tmp_price_1b * quantity, 2),
                                bitcoin=round(Wallet.objects.get(username=trans_seller.creator).bitcoin - quantity, 2))
                            messages.add_message(request, messages.INFO, 'Scambio avvenuto correttamente.')
                            return redirect('transaction_list')
                        else:
                            messages.add_message(request, messages.INFO, 'Transazione salvata.')
                            return redirect('transaction_list')

                    else:  # if he hasn't enaugh dollars
                        messages.add_message(request, messages.INFO, 'Devi inserire un prezzo positivo e che puoi sostenere.')
                        return redirect('transaction_list')
                else:
                    messages.add_message(request, messages.INFO, 'Non hai abbastanza dollari.')
                    return redirect('transaction_list')
            except Wallet.DoesNotExist:
                messages.add_message(request, messages.INFO,
                                     'Il tuo wallet non esiste ancora, l\'ho appena creato per te')
                return redirect('wallet')
    else:
        try:
            bit_user = Wallet.objects.get(username=request.user.username).bitcoin
            dol_user = Wallet.objects.get(username=request.user.username).dollars
            wallet_user = True
        except Wallet.DoesNotExist:
            messages.add_message(request, messages.INFO,
                                 'Il tuo wallet non esiste ancora, l\'ho appena creato per te')
            return redirect('wallet')
        form = Buy()
    return render(request, 'app/buy_edit.html', {'trans': form, 'bit_user': bit_user, 'dol_user': dol_user,
                                                 'wallet': wallet_user})


@login_required
def sell_new(request):
    if request.method == "POST":
        form = Sell(request.POST)
        if form.is_valid():
            trans_sell = form.save(commit=False)
            trans_sell.creator = request.user.username  # user
            trans_sell.buy_in = trans_sell.buy
            trans_sell.sell_in = trans_sell.sell
            trans_buyer = ""  # inizializzo

            try:
                trans_sell.bitcoin = Wallet.objects.get(username=trans_sell.creator).bitcoin
                trans_sell.dollars = Wallet.objects.get(username=trans_sell.creator).dollars

                # serve per capire se i valori sono +
                trans_sell.dollars_trans = trans_sell.price_1B_in * trans_sell.sell

                total_trans_sell = Trans.objects.all().filter(ended=False, good=True, buy=0, creator=trans_sell.creator)

                #  cerco se il SELLER ha abbastanza Bitcoin
                bitcoin_totali_in_vendita = trans_sell.sell
                for i in total_trans_sell:
                    bitcoin_totali_in_vendita += Trans.objects.get(_id=i._id).sell

                # se ho abbastanza B
                if bitcoin_totali_in_vendita <= trans_sell.bitcoin:
                    if trans_sell.dollars_trans > 0:    # se ha messo dollari positivi

                        # if the transition in good
                        Trans.objects.create(creator=trans_sell.creator, published_date=timezone.now(), good=True,
                                             buy=round(trans_sell.buy, 2), sell=round(trans_sell.sell, 2),
                                             buy_in=round(trans_sell.buy_in, 2),
                                             sell_in=round(trans_sell.sell_in, 2),
                                             price_1B_in=round(trans_sell.price_1B_in, 2))

                        trans_sell.id_sell = Trans.objects.latest('published_date')._id

                        tmp_price_1b = trans_sell.price_1B_in  # value of 1 bitcoin SELLER
                        quantity = 0  # bitcoin exchanged
                        buyer = ""  # tmp winner BUYER
                        id_buyer = 0  # buyer

                        #cerco le transazioni non self
                        total_trans = Trans.objects.all().filter(ended=False, good=True, sell=0).exclude(
                           creator=trans_sell.creator)

                        #   ovviamente non considero la possibilità che il venditore e il compratore siano la stessa
                        #   persona, non avrebbe senso

                        # cerco il BUYER
                        for k in total_trans:
                            trans_buyer_tmp = Trans.objects.get(_id=k._id)

                            # se ho abbastanza Bitcoin
                            if trans_buyer_tmp.price_1B_in > tmp_price_1b:  # a good buyer
                                trans_buyer = trans_buyer_tmp
                                tmp_price_1b = trans_buyer.price_1B_in  # prezzo di 1B temporaneo
                                buyer = trans_buyer.creator
                                id_buyer = trans_buyer._id

                                #valuto la quantità da scambiare
                                if trans_buyer.buy >= trans_sell.sell:  # match completo
                                    quantity = trans_sell.sell
                                else:  # match parziale
                                    quantity = trans_buyer.buy

                        if buyer != "":  # se c'è il BUYER

                            trans_sell.winner = buyer  # nome del BUYER
                            trans_sell.price_1B_end = tmp_price_1b  # prezzo di 1B
                            trans_sell.total_B_exchanged = quantity  # quantità di B scambiati
                            bitcoin_rimasti_buyer = trans_buyer.buy - quantity
                            bitcoin_rimasti_seller = trans_sell.sell - quantity

                            # BUYER
                            if bitcoin_rimasti_buyer == 0:  # buyer completa la transazione
                                Trans.objects.filter(_id=id_buyer).update(ended=True,
                                                                          total_price=round(tmp_price_1b * quantity, 2),
                                                                          winner=trans_sell.creator,
                                                                          price_1B_end=round(tmp_price_1b, 2),
                                                                          total_B_exchanged=round(quantity, 2), buy=0.0)

                            elif bitcoin_rimasti_buyer > 0:  # partial
                                Trans.objects.filter(_id=id_buyer).update(buy=bitcoin_rimasti_buyer)
                                Trans.objects.create(
                                    ended=True,
                                    good=True,
                                    creator=trans_buyer.creator,
                                    winner=trans_sell.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    buy=0.0,
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    buy_in=round(quantity, 2))
                            # SELLER
                            if bitcoin_rimasti_seller == 0:  #venditore completa la transazione
                                Trans.objects.filter(_id=trans_sell.id_sell).update(
                                    ended=True,
                                    winner=trans_buyer.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    sell=0.0)
                            elif bitcoin_rimasti_seller > 0:  # partial
                                Trans.objects.filter(_id=trans_sell.id_sell).update(sell=bitcoin_rimasti_seller)
                                Trans.objects.create(
                                    ended=True,
                                    good=True,
                                    total_price=round(tmp_price_1b * quantity, 2),
                                    creator=trans_sell.creator,
                                    winner=trans_buyer.creator,
                                    price_1B_end=round(tmp_price_1b, 2),
                                    total_B_exchanged=round(quantity, 2),
                                    sell=0.0, sell_in=round(quantity, 2))
                            # aggiorna il wallet
                            Wallet.objects.filter(username=trans_sell.creator).update(
                                dollars=round(Wallet.objects.get(username=trans_sell.creator).dollars +
                                              tmp_price_1b * quantity, 2),

                                bitcoin=round(Wallet.objects.get(username=trans_sell.creator).bitcoin - quantity, 2),
                            )

                            Wallet.objects.filter(username=buyer).update(
                                dollars=round(Wallet.objects.get(
                                    username=trans_buyer.creator).dollars - tmp_price_1b * quantity, 2),

                                bitcoin=round(Wallet.objects.get(username=trans_buyer.creator).bitcoin + quantity, 2))

                            messages.add_message(request, messages.INFO, 'Scambio avvenuto')
                            return redirect('transaction_list')
                        else:
                            messages.add_message(request, messages.INFO, 'Transazione salvata.')
                            return redirect('transaction_list')

                    # se non ha scritto dollari positivi
                    else:
                        messages.add_message(request, messages.INFO, 'Errore: Inserisci il prezzo positivo.')
                        return redirect('transaction_list')

                # se non ha abbastanza Bitcoin
                else:
                    messages.add_message(request, messages.INFO, 'Non hai abbastanza Bitcoin.')
                    return redirect('transaction_list')

            except Wallet.DoesNotExist:
                messages.add_message(request, messages.INFO,
                                     'Il tuo wallet non esiste ancora, l\'ho appena creato per te')
                return redirect('wallet')
    else:
        try:
            bit_user = Wallet.objects.get(username=request.user.username).bitcoin
            dol_user = Wallet.objects.get(username=request.user.username).dollars
            wallet_user = True
        except Wallet.DoesNotExist:
            messages.add_message(request, messages.INFO,
                                 'Il tuo wallet non esiste ancora, l\'ho appena creato per te')
            return redirect('wallet')

        form = Sell()
    return render(request, 'app/sell_edit.html', {'trans': form, 'bit_user': bit_user,'dol_user': dol_user,
                                                  'wallet': wallet_user})


@login_required
def transaction_detail(request, pk):
    trans = get_object_or_404(Trans, pk=pk)
    try:
        return render(request, 'app/transaction_detail.html', {'trans': trans})
    except Wallet.DoesNotExist:
        trans.wallet = False
        return render(request, 'app/transaction_detail.html', {'trans': trans})


#   lista pubblica di tutte le transazioni
def transaction_list(request):
    transs = Trans.objects.filter(published_date__lte=timezone.now(), good=True).order_by('published_date')
    try:
        transs.bit_user = round(Wallet.objects.get(username=request.user.username).bitcoin, 2)
        transs.dol_user = round(Wallet.objects.get(username=request.user.username).dollars, 2)
        transs.wallet = True
        return render(request, 'app/transaction_list.html', {'transs': transs})
    except Wallet.DoesNotExist:
        transs.wallet = False
        return render(request, 'app/transaction_list.html', {'transs': transs})


@login_required
def transaction_active_list(request):  # lista pubblica delle transazioni attive
    transs = Trans.objects.filter(published_date__lte=timezone.now(), ended=False, good=True).order_by('published_date')
    try:
        transs.bit_user = round(Wallet.objects.get(username=request.user.username).bitcoin, 2)
        transs.dol_user = round(Wallet.objects.get(username=request.user.username).dollars, 2)
        transs.wallet = True
        return render(request, 'app/transaction_active_list.html', {'transs': transs})
    except Wallet.DoesNotExist:
        transs.wallet = False
        return render(request, 'app/transaction_active_list.html', {'transs': transs})


@login_required
def earn_lose(request):    # bilancio
    try:
        transs = Trans.objects.filter(
            Q(creator=request.user.username, published_date__lte=timezone.now(), ended=True)
            | Q(winner=request.user.username, published_date__lte=timezone.now(), ended=True)
        ).order_by('published_date')  # cerco se l'user è creator o winner

        transs.bit_in = round(Wallet.objects.get(username=request.user.username).bitcoin_init, 2)
        transs.dol_in = round(Wallet.objects.get(username=request.user.username).dollars_init, 2)
        transs.bit_fin = round(Wallet.objects.get(username=request.user.username).bitcoin, 2)
        transs.dol_fin = round(Wallet.objects.get(username=request.user.username).dollars, 2)
        transs.dol_diff = round(transs.dol_fin - transs.dol_in, 2)
        transs.bit_diff = round(transs.bit_fin - transs.bit_in, 2)

        return render(request, 'app/earn_lose.html', {'transs': transs})

    except Wallet.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Non hai un Wallet, e quindi non puoi avere un bilancio. Ora te lo creo io!')
        return redirect('wallet')


@login_required
def transaction_remove(request, pk):   # rimuove la transazione
    trans = get_object_or_404(Trans, pk=pk)
    if trans.creator == request.user.username:  # solo il creatore può farlo
        messages.add_message(request, messages.INFO, 'Transazione cancellata.')
        trans.delete()
    else:
        messages.add_message(request, messages.INFO, 'La puoi concludere solo se sei il creatore della transazione.')
    return redirect('transaction_list')


@login_required
def transaction_new(request):
    try:
        bit_user = round(Wallet.objects.get(username=request.user.username).bitcoin, 2)
        dol_user = round(Wallet.objects.get(username=request.user.username).dollars, 2)
        wallet_user = True
        return render(request, 'app/transaction_new.html',
                      {'bit_user': bit_user, 'dol_user': dol_user, 'wallet': wallet_user})

    except Wallet.DoesNotExist:
        wallet_user = False
        return render(request, 'app/transaction_new.html',
                      {'wallet': wallet_user})
