from typing import Any
from cplex import *
import numpy as np
import math
import matplotlib.pyplot  as plt 

#Nomi dei modelli associati al valore del costo ottimo dei problemi
fileName = {}
#Nomi dei modelli associati al numero di variabili "fixed"
fixed = {}
#Nomi dei modelli associati al numero di variabili "tighted"
tightened = {}
#Nomi dei modelli associati al numero di variabili totale
var = {}

#Funzione lambda per il calcolo del bound tramite il costo ridotto
bd = lambda bo, inc, ot, rc : bo + (float(inc) - ot)/rc 
bd2 = lambda bo, inc, ot, rc : bo + ((float(inc) - ot)/2)/rc 


def readTxt(filename):
    with open(filename) as f:
        line = f.readlines()
    for r in line:
        #Riempie il dizionario con i nomi dei file(dei modelli MIP) associati alla soluzione ottima
        fileName[r.split()[0]]=r.split()[1]
        #Riempie il dizionario con i nomi dei modelli MIP e setta a 0 i contatori
        fixed[r.split()[0]]=tightened[r.split()[0]]=0
        

def readProblems(cpxRel,ext,la):
    var_type= []
    #Scorro il dizionario con i nomi file dei modelli, apro il modello 
    for name in fileName.keys():
        cpxRel.read(name,ext)
        
        var_type.clear()
        var_type=cpxRel.variables.get_types()
        
        #Applica un rilassamento
        cpxRel.set_problem_type(cpxRel.problem_type.LP)
       
        #Chiama la funzione che calcola il bound
        #Passo anche la funzione lambda da utilizzare per il calcolo del bound
        getBound(cpxRel,var_type,la)
                        
#Scrive sul file result.txt il risultato delle iterazioni, formato del file:
# "nomeProblema"  "# var fissate" "# var ristrette" "# var totali"                 
def writeToFile(result):
    f = open(result, "a")
    for n in fixed.keys():
        f.write('%s  %s  %s  %s  \n' % (n, str(fixed.get(n)), str(tightened.get(n)), str(var.get(n)) )) 
    f.close()


def getBound(cpxRel,var_type,la):
    #Assegnamento del costo ottimo del problema come incumbent
    incumbent=fileName[cpxRel.get_problem_name()]

    #Risoluzione del problema LP
    cpxRel.solve()
    # cpxRel.solution.basis.get_basis()[0][i]
    #   status:
    #
    #   0 lower bound
    #   1 basic(in base)
    #   2 upper bound
    
    # cpxRel.objective.get_sense()
    # 
    # 1 minimize
    # -1 maximize
    
    
    #Liste di indici, rispettivamente contenenti gli indici delle variabili ad upper e a lower bound(tutte le variabili fuori base)
    lo = [i for i, x in enumerate(cpxRel.solution.basis.get_basis()[0]) if x==0]
    up = [i for i, x in enumerate(cpxRel.solution.basis.get_basis()[0]) if x==2]
     
    #Costo ottimo del rilassamento
    ot=cpxRel.solution.get_objective_value()
    #Vettore dei costi ridotti
    rc=cpxRel.solution.get_reduced_costs()
    #Dizionario con numero di variabili totale del problema
    var[cpxRel.get_problem_name()] = cpxRel.variables.get_num()
    
    #Scorro gli indici delle variabili a lower bound
    for i in lo:
        #Ottengo il nome della variabile
        x = cpxRel.variables.get_names(i)
        #Se la variabile fuori base è a LB
        if((rc[i] > 0 and cpxRel.objective.get_sense() == 1) or (rc[i] < 0 and cpxRel.objective.get_sense() == -1)):
            #Nel dizionario "tightened" aggiorno il contatore delle variabili "ristrette"
            tightened[cpxRel.get_problem_name()] += 1
            lbs = cpxRel.variables.get_lower_bounds(x)
            #Valore di Upper Bound calcolato tramite la formula con i costi ridotti
            ub = la(lbs,incumbent,ot,rc[i])
            #Se variabile intera:
            if(var_type[i] == cpxRel.variables.type.integer):
                #Applicare parte intera bassa
                ub = math.floor(ub)
            #Se variabile binaria:
            elif(var_type[i] == cpxRel.variables.type.binary):
                ub = math.floor(ub)
                #In caso di variabile binaria il lower bound "implicito" è '0', lo esplicito
                lbs=0
                 
            # In ogni caso, anche se la variabile non è ne intera ne binaria,
            # posso fissarla se il lowerbound calcolato corrisponde all' upperbound dato dal problema
            
            #Nel dizionario "fixed" aggiorno il contatore delle variabili fissate
            if ub==lbs: fixed[cpxRel.get_problem_name()] += 1
                        
    for i in up:
        x = cpxRel.variables.get_names(i)
        #Se la variabile fuori base è ad UB
        if((rc[i] < 0 and cpxRel.objective.get_sense() == 1) or (rc[i] > 0 and cpxRel.objective.get_sense() == -1)):
            tightened[cpxRel.get_problem_name()] += 1
            ubs = cpxRel.variables.get_upper_bounds(x)
            lb = la(ubs,incumbent,ot,-rc[i])
            if(var_type[i] == cpxRel.variables.type.integer):
                #In caso di variabile intera posso arrotondare alla parte intera alta
                lb = math.ceil(lb)
            elif(var_type[i] == cpxRel.variables.type.binary):
                lb = math.ceil(lb)
                #In caso di variabile binaria l' upper bound "implicito" è '1', lo esplicito
                ubs=1
           
            if lb==ubs: fixed[cpxRel.get_problem_name()] += 1
        

#Disegna e salva su file i grafici riassuntivi
def draw(result,red,tight,testset):
    #Lista che contiene le percentuali di var fissate su le variabili totali di ogni problema
    percFix = []
    percTig = []
        
    with open(result) as r:
        lines = list(filter(None, (line.rstrip() for line in r)))

    for l in lines:
        #Aggiunge alla lista la percentuale 
        percFix.append((int(l.split()[1])/int(l.split()[3])) * 100)
        percTig.append((int(l.split()[2])/int(l.split()[3])) * 100)
    r.close()
     
    #Ordina le percentuali in ordine crescente in modo da ottenere una funzione monotona
    percFix = sorted(percFix)
    percTig = sorted(percTig)
    
    #  Grafico Reduced cost fixing
    
    plt.figure(figsize=(15,6))
    plt.title('Reduced cost fixing')
    plt.xlabel("Benchmark testset: "+testset+" models")
    plt.ylabel('% of fixed Variables')
    #I punti dell'asse X vanno da 1 al numero di modelli presi in considerazione
    xpoints = np.array(range(1,len(percFix)+1))
    #Sui punti dell'asse Y sono proiettate le percentuali
    ypoints = np.array(percFix)
    plt.plot(xpoints,ypoints,'midnightblue')
    #Plotta una retta che identifica la percentuale media di var fissate
    plt.axhline(y=np.nanmean(percFix),color='royalblue', ls='--', label="average")
    #Imposta un testo che mostra il valore medio di var fissate
    plt.text(0,np.nanmean(percFix), "{:.2f}".format(np.nanmean(percFix)) + "%", color="royalblue", ha="left", va="bottom")
    plt.grid()
    #Salva su file
    plt.savefig(red)
    plt.show()
    
    
    #  Grafico Reduced cost tightening
    
    plt.figure(figsize=(15,6))
    plt.title('Reduced cost tightening')
    plt.xlabel("Benchmark testset: "+testset+" models")
    plt.ylabel('% of tightened Variables')
    ypoints = np.array(percTig)
    plt.plot(xpoints,ypoints,'darkred')
    plt.axhline(y=np.nanmean(percTig),color='coral', ls='--', label="average")
    plt.text(0,np.nanmean(percTig), "{:.2f}".format(np.nanmean(percTig))+ "%", color="coral", ha="left", va="bottom")
    plt.grid()
    plt.savefig(tight)
    plt.show()
        
def drawCompare(result1, result2, rescompare,testset):
    percFix1 = []
    percFix2 = []

    with open(result1) as r:
        lines1 = list(filter(None, (line.rstrip() for line in r)))
    with open(result2) as r:
        lines2 = list(filter(None, (line.rstrip() for line in r)))

    r.close()

    for l1 in lines1:
        percFix1.append((int(l1.split()[1])/int(l1.split()[3])) * 100)    
    for l2 in lines2:
        percFix2.append((int(l2.split()[1])/int(l2.split()[3])) * 100)
    
    #               Ordina le 2 liste "sincronizzandole"
    #Zippa le 2 liste in una sola lista (di tuple) in formato:   [(percFix1, percFix2),..]
    ls = list(zip(percFix1,percFix2))
    sortedList = sorted(ls, key = lambda x: x[0])
    #Unzip ricostruendo le 2 liste ordinate secondo la prima
    percFix1 = [i for i, j in sortedList]
    percFix2 = [j for i, j in sortedList]
    
    #  Grafico Reduced cost fixing comparato
    plt.figure(figsize=(15,6))
    plt.title('Reduced cost fixing')
    plt.xlabel("Benchmark testset: "+testset+" models")
    plt.ylabel('% of fixed Variables')
    x = np.array(range(1,len(percFix1)+1))
    y1 = np.array(percFix1)
    y2 = np.array(percFix2)
        
    
    plt.text(1, 105, "Halved Gap improvement: " + str("{:.2f}".format(y2.mean() - y1.mean())) + "%",fontsize=15, color="purple")
    plt.plot(x, y1, label = "Real GAP",color='mediumslateblue' ) 
    plt.plot(x, y2, label = "Halved GAP",color='hotpink') 
    plt.legend() 
    
    plt.grid()
    plt.savefig(rescompare)
    plt.show()
    
def clear():
    fixed.clear()
    tightened.clear()
    fileName.clear()
    var.clear()
    
if __name__ == '__main__':
    cpxRel = Cplex()
    cpxRel.parameters.read_file('settings.prm')
    
    #Legge miplib2017.txt che contiene il nome dei modelli della libreria miplib e il relativo valore ottimo    
    readTxt("miplib2017.txt")
     
    #Legge i problemi da file, calcola il bound tramite la funzione lambda passata come parametro, e conta le variabili fixed e thighted
    #Inoltre passo il formato dei file da aprire 
    readProblems(cpxRel,"mps",bd)
    
    #   Scrive i risultati su "miplibres.txt"
    writeToFile("miplibres.txt")
    
    
    #   Disegna i grafici a partire da "miplibres.txt"
    draw('miplibres.txt','reduced_plot.png','tightened_plot.png',"MIPLIB2017")
    #Pulisce tutte le strutture dati
    clear()
    
    
    #   Stesso metodo sul nuovo testset
    readTxt("setpart.txt")
    readProblems(cpxRel,"lp",bd)
    writeToFile("setpartres.txt")
    draw('setpartres.txt','setpart_reduced_plot.png','setpart_tightened_plot.png',"SETPART")
    clear()
    
    
    #       Ora con Bound dimezzato su miplib2017
    readTxt("miplib2017.txt")
    readProblems(cpxRel,"mps",bd2)
    writeToFile("miplibres2.txt")
    draw('miplibres2.txt','reduced_plot2.png','tightened_plot2.png',"MIPLIB2017")
    clear()
    
    #       Con Bound dimezzato su setpart
    readTxt("setpart.txt")
    readProblems(cpxRel,"lp",bd2)
    writeToFile("setpartres2.txt")
    draw('setpartres2.txt','setpart_reduced_plot2.png','setpart_tightened_plot2.png',"SETPART")
    clear()
    

    #       Disegna il grafico di confronto tra i 2 metodi applicati a miplib2017
    drawCompare('miplibres.txt','miplibres2.txt', "miplibcompared.png","MIPLIB2017")
    drawCompare('setpartres.txt','setpartres2.txt', "setpartcompared.png","SETPART")

    
    
    
    




    
    

    
    
