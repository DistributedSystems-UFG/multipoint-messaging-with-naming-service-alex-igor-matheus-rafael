[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/YsEblNIV)

# Truco online UDP

Jogo de truco com comunicação multicast entre peers para a matéria de Sistemas Distribuídos.

## Como rodar

1. Ligue 5 máquinas (4 peers, 1 server).

2. Edite `constMP.py` e configure `GROUPMNGR_ADDR` com o IP público da máquina que executará o servidor.

3. Clone o repositório nas 5 máquinas ou no sistema de arquivos compartilhado `/mnt/efs/fs1/`.

4. Execute o `groupMngr.py` na máquina 1 (servidor).

5. Execute `peerComunicatorUDP.py` nas 4 máquinas peers.

6. Em cada um dos 4 peers, você controla as jogadas como se fosse um jogador.

## Como funciona

Cada peer é um jogador na mesa de truco. O servidor serve para iniciar cada rodada, manter o placar do jogo e distribuir as cartas, funciona como um "dealer". Cada mão é jogada apenas por comunicação entre os peers via UDP. A troca de mensagens do programa anterior agora funciona como "troca de jogadas". Cada peer espera sua vez de jogar e atualiza o estado da mão (vaza, tentos da mão, cartas na mesa, vazas de cada time, pedidos de truco/6/12) e identifica se o jogo acabou localmente. Na sua vez, o peer envia sua jogada para todos os outros peers. O peer 0 requisita atualização do placar no server com o ganhador da mão e quantos tentos (pontos), que envia de novo a ordem da mesa e sorteia as cartas de cada peer (jogador). O jogo encerra em todos os peers quando algum time faz 12 pontos.Peer <-> Peer: UDP | Peer <-> Servidor: TCP.

## Relação com a ordenação das mensagens

A ordem das mensagens agora é essencial para manter a consistência da partida. Por exemplo, se um peer receber uma jogada do jogador 2 antes da jogada esperada do jogador 1, sua visão da mesa pode ficar incorreta. Isso pode causar erros na vez de jogar, no cálculo do vencedor da vaza ou no valor da mão.

Assim, a aplicação evidencia a importância da ordenação: em um jogo distribuído, todos os peers precisam processar os eventos na mesma sequência para manter o mesmo estado da partida.
