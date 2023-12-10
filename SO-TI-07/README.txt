### Grupo: SO-TI-07
### Aluno 1: Diogo Forte (fc56931)
### Aluno 2: Gonçalo Gouveia (fc60289)
### Aluno 3: João Vaz (fc58283)

### Exemplos de comandos para executar o pwordcount:
1) ./pwordcount -m t -p 1 teste1.txt
2) ./pwordcount -m u -p 1 teste2.txt
3) ./pwordcount -m o -p 1 midsummer.txt 
4) ./pwordcount -m t -p 4 midsummer.txt teste1.txt
4) ./pwordcount -m t -p 2 midsummer.txt

### Limitações da implementação:
- Nao divide ficheiros se o numero de ficheiros dado for superior a 1;
- Não há comunicação entre processos, cada processo imprime o que lhe foi pedido.

### Abordagem para a divisão dos ficheiros:
- Se a paralelização for igual ou maior do que o número de ficheiros introduzidos,
o programa atribui a cada processo um único ficheiro, com o último sendo dividido entre os processos restantes
- Se a paralelização for menor do que o número de ficheiros introduzidos, a divisão
é feita da forma mais equitativa possível entre os processos disponíveis;
- No caso excepcional de apenas um ficheiro ser introduzido e a paralelização for 
superior a 1, o programa divide o ficheiro em função do número de processos disponíveis,
ficando cada processo com uma quantidade equitativa de conteúdo para ler.


