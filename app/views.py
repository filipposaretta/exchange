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
    try:
        user.bitcoin = Wallet.objects.get(username=request.user.username).bitcoin
        user.dollars = Wallet.objects.get(username=request.user.username).dollars
        return render(request, 'app/wallet.html', {'user': user})
    except Wallet.DoesNotExist:  # new user
        user.bitcoin = random.random() * 10
        while user.bitcoin < 1:
            user.bitcoin = random.random() * 10
        user.dollars = random.random() * 150000
        user.save()
        Wallet.objects.create(username=user.username, bitcoin=user.bitcoin, dollars=user.dollars,
                              dollars_init=user.dollars, bitcoin_init=user.bitcoin)
        return render(request, 'app/wallet.html', {'user': user})


@login_required
def buy_new(request):
    if request.method == "POST":
        form = Buy(request.POST)
        if form.is_valid():
            trans_buyer = form.save(commit=False)
            trans_buyer.creator = request.user.username  # user
            trans_buyer.buy_in = trans_buyer.buy
            trans_buyer.sell_in = trans_buyer.sell
            trans_seller = ""
            try:
                dollars_B = Wallet.objects.get(username=trans_buyer.creator).dollars
                trans_buyer.dollars_trans = trans_buyer.one_B_dollar * trans_buyer.buy  # is a check for the positivity of values

                if 0 < trans_buyer.dollars_trans < dollars_B:  # if I have a good tran
                    Trans.objects.create(creator=trans_buyer.creator, published_date=timezone.now(), good=True,
                                         buy=trans_buyer.buy, sell=0, buy_in=trans_buyer.buy_in, sell_in=0,
                                         one_B_dollar=trans_buyer.one_B_dollar)

                    trans_buyer.id_buyer = Trans.objects.latest('published_date')._id

                    tmp_one_bit_dollars = trans_buyer.one_B_dollar  # value of 1 bitcoin BUYER
                    tmp_one_bit_dollars_seller = 0
                    quantity = 0
                    seller = ""  # tmp winner SELLER
                    id_seller = 0

                    total_trans = Trans.objects.all().filter(ended=False, good=True, buy=0).exclude(
                        creator=trans_buyer.creator)

                    for k in total_trans:  # for each transaction we look for the SELLER
                        trans_seller_tmp = Trans.objects.get(_id=k._id)
                        if tmp_one_bit_dollars >= trans_seller_tmp.one_B_dollar > tmp_one_bit_dollars_seller:  # a good seller
                            trans_seller = trans_seller_tmp
                            tmp_one_bit_dollars_seller = trans_seller.one_B_dollar
                            seller = trans_seller.creator
                            id_seller = trans_seller._id
                            if trans_seller.sell >= trans_buyer.buy:  # match completo
                                quantity = trans_buyer.buy
                            else:  # match parziale
                                quantity = trans_seller.sell

                    if seller != "":  # if there is a winner, winner = seller
                        trans_buyer.winner = seller
                        trans_buyer.price_1B_sell = tmp_one_bit_dollars
                        trans_buyer.quantity_B_sell = quantity
                        bitcoin_rimasti_seller = trans_seller.sell - quantity
                        bitcoin_rimasti_buyer = trans_buyer.buy - quantity  # buyer

                        # SELLER
                        if bitcoin_rimasti_seller <= 0:  # complete seller
                            Trans.objects.filter(_id=id_seller).update(
                                ended=True,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                winner=trans_buyer.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                sell=0)

                        elif bitcoin_rimasti_seller > 0:  # partial
                            Trans.objects.filter(_id=id_seller).update(sell=bitcoin_rimasti_seller)
                            Trans.objects.create(
                                creator=trans_seller.creator,
                                ended=True,
                                good=True,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                winner=trans_buyer.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                sell=0, sell_in=quantity)

                        # BUYER
                        if bitcoin_rimasti_buyer <= 0:
                            Trans.objects.filter(_id=trans_buyer.id_buyer).update(
                                ended=True,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                winner=trans_seller.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                buy=0)
                        elif bitcoin_rimasti_buyer > 0:  # partial
                            Trans.objects.filter(_id=trans_buyer.id_buyer).update(buy=bitcoin_rimasti_buyer)
                            Trans.objects.create(
                                creator=trans_buyer.creator,
                                good=True,
                                ended=True,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                winner=trans_seller.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                buy=0, buy_in=quantity)

                        Wallet.objects.filter(username=trans_buyer.creator).update(
                            dollars=Wallet.objects.get(
                                username=trans_buyer.creator).dollars - tmp_one_bit_dollars * quantity,
                            bitcoin=Wallet.objects.get(username=trans_buyer.creator).bitcoin + quantity)

                        Wallet.objects.filter(username=trans_seller.creator).update(
                            dollars=Wallet.objects.get(
                                username=trans_seller.creator).dollars + tmp_one_bit_dollars * quantity,
                            bitcoin=Wallet.objects.get(username=trans_seller.creator).bitcoin - quantity)
                        messages.add_message(request, messages.INFO, 'Scambio avvenuto correttamente.')
                        return redirect('transaction_list')
                    else:
                        messages.add_message(request, messages.INFO, 'Transazione salvata.')
                        return redirect('transaction_list')

                else:  # if he hasn't enaugh dollars
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
            wallet_user = False
        form = Buy()
    return render(request, 'app/buy_edit.html', {'trans': form, 'bit_user': bit_user,
                                                  'dol_user': dol_user, 'wallet': wallet_user})


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
                trans_sell.dollars_trans = trans_sell.one_B_dollar * trans_sell.sell  # is a check for the positivity of values
                if trans_sell.dollars_trans > 0 and trans_sell.sell <= trans_sell.bitcoin:
                    # if the transition in good
                    Trans.objects.create(creator=trans_sell.creator, published_date=timezone.now(), good=True,
                                         buy=trans_sell.buy, sell=trans_sell.sell, buy_in=trans_sell.buy_in,
                                         sell_in=trans_sell.sell_in, one_B_dollar=trans_sell.one_B_dollar)

                    trans_sell.id_sell = Trans.objects.latest('published_date')._id

                    tmp_one_bit_dollars = trans_sell.one_B_dollar  # value of 1 bitcoin SELLER
                    quantity = 0  # bitcoin exchanged
                    buyer = ""  # tmp winner BUYER
                    id_buyer = 0  # buyer

                    total_trans = Trans.objects.all().filter(ended=False, good=True, sell=0).exclude(
                        creator=trans_sell.creator)
                    for k in total_trans:  # for each transaction we look for the BUYER
                        trans_buyer_tmp = Trans.objects.get(_id=k._id)
                        # OK
                        if trans_buyer_tmp.one_B_dollar >= tmp_one_bit_dollars:  # a good buyer
                            trans_buyer = trans_buyer_tmp
                            tmp_one_bit_dollars = trans_buyer.one_B_dollar  # value of 1 bitcoin
                            buyer = trans_buyer.creator
                            id_buyer = trans_buyer._id
                            if trans_buyer.buy >= trans_sell.sell:  # match completo
                                quantity = trans_sell.sell
                            else:  # match parziale
                                quantity = trans_buyer.buy

                    if buyer != "":  # if there is a buyer

                        trans_sell.winner = buyer  # name of the buyer
                        trans_sell.price_1B_sell = tmp_one_bit_dollars  # price of 1 bitcoin exchanged
                        trans_sell.quantity_B_sell = quantity  # quantity of B exchanged
                        bitcoin_rimasti_buyer = trans_buyer.buy - quantity  # for the transaction
                        bitcoin_rimasti_seller = trans_sell.sell - quantity  # seller

                        # BUYER
                        if bitcoin_rimasti_buyer <= 0:  # buyer complete the transaction
                            Trans.objects.filter(_id=id_buyer).update(ended=True,
                                                                      total_dollars_sell=tmp_one_bit_dollars * quantity,
                                                                      winner=trans_sell.creator,
                                                                      price_1B_sell=tmp_one_bit_dollars,
                                                                      quantity_B_sell=quantity, buy=0)

                        elif bitcoin_rimasti_buyer > 0:  # partial
                            Trans.objects.filter(_id=id_buyer).update(buy=bitcoin_rimasti_buyer)
                            Trans.objects.create(
                                ended=True,
                                good=True,
                                creator=trans_buyer.creator,
                                winner=trans_sell.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                buy=0,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                buy_in=quantity)
                        # SELLER
                        if bitcoin_rimasti_seller <= 0:
                            Trans.objects.filter(_id=trans_sell.id_sell).update(
                                ended=True,
                                winner=trans_buyer.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                sell=0)
                        elif bitcoin_rimasti_seller > 0:  # partial
                            Trans.objects.filter(_id=trans_sell.id_sell).update(sell=bitcoin_rimasti_seller)
                            Trans.objects.create(
                                ended=True,
                                good=True,
                                total_dollars_sell=tmp_one_bit_dollars * quantity,
                                creator=trans_sell.creator,
                                winner=trans_buyer.creator,
                                price_1B_sell=tmp_one_bit_dollars,
                                quantity_B_sell=quantity,
                                sell=0, sell_in=quantity)
                        # update the wallet
                        Wallet.objects.filter(username=trans_sell.creator).update(
                            dollars=Wallet.objects.get(
                                username=trans_sell.creator).dollars + tmp_one_bit_dollars * quantity,
                            bitcoin=Wallet.objects.get(username=trans_sell.creator).bitcoin - quantity
                        )

                        Wallet.objects.filter(username=buyer).update(
                            dollars=Wallet.objects.get(
                                username=trans_buyer.creator).dollars - tmp_one_bit_dollars * quantity,
                            bitcoin=Wallet.objects.get(username=trans_buyer.creator).bitcoin + quantity)
                        messages.add_message(request, messages.INFO, 'Scambio avvenuto')
                        return redirect('transaction_list')
                    else:
                        messages.add_message(request, messages.INFO, 'Transazione salvata.')
                        return redirect('transaction_list')

                else:  # if he hasn't enaugh bitcoin
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
            wallet_user = False
        form = Sell()
    return render(request, 'app/sell_edit.html', {'trans': form, 'bit_user': bit_user,
                                                  'dol_user': dol_user, 'wallet': wallet_user})

@login_required
def transaction_detail(request, pk):
    trans = get_object_or_404(Trans, pk=pk)
    try:
        return render(request, 'app/transaction_detail.html', {'trans': trans})
    except Wallet.DoesNotExist:
        trans.wallet = False
        return render(request, 'app/transaction_detail.html', {'trans': trans})


def transaction_list(request):  # this is public list of all transactions
    transs = Trans.objects.filter(published_date__lte=timezone.now(), good=True).order_by('published_date')
    try:
        transs.bit_user = Wallet.objects.get(username=request.user.username).bitcoin
        transs.dol_user = Wallet.objects.get(username=request.user.username).dollars
        transs.wallet = True
        return render(request, 'app/transaction_list.html', {'transs': transs})
    except Wallet.DoesNotExist:
        transs.wallet = False
        return render(request, 'app/transaction_list.html', {'transs': transs})


@login_required
def transaction_active_list(request):  # this is public list of active transactions
    transs = Trans.objects.filter(published_date__lte=timezone.now(), ended=False, good=True).order_by('published_date')
    try:
        transs.bit_user = Wallet.objects.get(username=request.user.username).bitcoin
        transs.dol_user = Wallet.objects.get(username=request.user.username).dollars
        transs.wallet = True
        return render(request, 'app/transaction_active_list.html', {'transs': transs})
    except Wallet.DoesNotExist:
        transs.wallet = False
        return render(request, 'app/transaction_active_list.html', {'transs': transs})


@login_required
def earn_lose(request):
    try:
        transs = Trans.objects.filter(
            Q(creator=request.user.username, published_date__lte=timezone.now(), ended=True)
            | Q(winner=request.user.username, published_date__lte=timezone.now(), ended=True)
        ).order_by('published_date')  # sell

        transs.bit_in = Wallet.objects.get(username=request.user.username).bitcoin_init
        transs.dol_in = Wallet.objects.get(username=request.user.username).dollars_init
        transs.bit_fin = Wallet.objects.get(username=request.user.username).bitcoin
        transs.dol_fin = Wallet.objects.get(username=request.user.username).dollars
        transs.dol_diff = transs.dol_fin - transs.dol_in
        transs.bit_diff = transs.bit_fin - transs.bit_in
        return render(request, 'app/earn_lose.html', {'transs': transs})
    except Wallet.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Non hai un Wallet, e quindi non puoi avere un bilancio. Ora te lo creo io!')
        return redirect('wallet')


@login_required
def transaction_remove(request, pk):
    trans = get_object_or_404(Trans, pk=pk)
    if trans.creator == request.user.username:  # only the creator can conclude the transaction
        messages.add_message(request, messages.INFO, 'Transazione cancellata.')
        trans.delete()
    else:
        messages.add_message(request, messages.INFO, 'La puoi concludere solo se sei il creatore della transazione.')
    return redirect('transaction_list')


def transaction_new(request):
    try:
        bit_user = Wallet.objects.get(username=request.user.username).bitcoin
        dol_user = Wallet.objects.get(username=request.user.username).dollars
        wallet_user = True
        return render(request, 'app/transaction_new.html',
                      {'bit_user': bit_user, 'dol_user': dol_user, 'wallet': wallet_user})

    except Wallet.DoesNotExist:
        wallet_user = False
        return render(request, 'app/transaction_new.html',
                      {'wallet': wallet_user})
